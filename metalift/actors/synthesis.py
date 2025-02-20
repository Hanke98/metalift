import os

from metalift.analysis import CodeInfo, analyze
from metalift.ir import *

from llvmlite.binding import ValueRef

import typing
from typing import Callable, Union, Protocol

from metalift.synthesis_common import SynthesisFailed, VerificationFailed


def observeEquivalence(
    inputState: Expr, synthState: Expr, queryParams: typing.List[Var]
) -> Expr:
    return Call("equivalence", Bool(), inputState, synthState, *queryParams)


def opsListInvariant(
    fnNameBase: str, synthState: Expr, synthStateType: Type, opType: Type
) -> Expr:
    return And(
        Eq(
            Call(
                "apply_state_transitions",
                synthStateType,
                TupleGet(synthState, IntLit(len(synthStateType.args) - 1)),
                Var(
                    f"{fnNameBase}_next_state",
                    Fn(synthStateType, synthStateType, *opType.args),
                ),
                Var(
                    f"{fnNameBase}_init_state",
                    Fn(synthStateType),
                ),
            ),
            synthState,
        ),
        Call(
            "ops_in_order",
            Bool(),
            TupleGet(synthState, IntLit(len(synthStateType.args) - 1)),
        ),
    )


def supportedCommand(synthState: Expr, args: typing.Any) -> Expr:
    return Call("supportedCommand", Bool(), synthState, *args)


def unpackOp(op: Expr) -> typing.List[Expr]:
    if op.type.name == "Tuple":
        return [TupleGet(op, IntLit(i)) for i in range(len(op.type.args))]
    else:
        return [op]


def opListAdditionalFns(
    synthStateType: Type,
    opType: Type,
    initState: Callable[[], Expr],
    inOrder: Callable[[typing.Any, typing.Any], Expr],
    opPrecondition: Callable[[typing.Any], Expr],
) -> typing.List[Union[FnDecl, FnDeclNonRecursive, Axiom]]:
    def list_length(l: Expr) -> Expr:
        return Call("list_length", Int(), l)

    def list_get(l: Expr, i: Expr) -> Expr:
        return Call("list_get", opType, l, i)

    def list_tail(l: Expr, i: Expr) -> Expr:
        return Call("list_tail", List(opType), l, i)

    data = Var("data", List(opType))
    next_state_fn = Var(
        "next_state_fn",
        Fn(
            synthStateType,
            synthStateType,
            *(opType.args if opType.name == "Tuple" else [opType]),
        ),
    )

    init_state_fn = Var("init_state_fn", Fn(synthStateType))

    reduce_fn = FnDecl(
        "apply_state_transitions",
        synthStateType,
        Ite(
            Eq(list_length(data), IntLit(0)),
            CallValue(init_state_fn),
            CallValue(
                next_state_fn,
                Call(
                    "apply_state_transitions",
                    synthStateType,
                    list_tail(data, IntLit(1)),
                    next_state_fn,
                    init_state_fn,
                ),
                *(
                    [
                        # TODO(shadaj): unnecessary cast
                        typing.cast(
                            Expr, TupleGet(list_get(data, IntLit(0)), IntLit(i))
                        )
                        for i in range(len(opType.args))
                    ]
                    if opType.name == "Tuple"
                    else [list_get(data, IntLit(0))]
                ),
            ),
        ),
        data,
        next_state_fn,
        init_state_fn,
    )

    next_op = Var("next_op", opType)
    ops_in_order_helper = FnDecl(
        "ops_in_order_helper",
        Bool(),
        And(
            opPrecondition(unpackOp(next_op)),
            Ite(
                Eq(list_length(data), IntLit(0)),
                BoolLit(True),
                And(
                    inOrder(unpackOp(list_get(data, IntLit(0))), unpackOp(next_op)),
                    Call(
                        "ops_in_order_helper",
                        Bool(),
                        list_get(data, IntLit(0)),
                        list_tail(data, IntLit(1)),
                    ),
                ),
            ),
        ),
        next_op,
        data,
    )

    ops_in_order = FnDecl(
        "ops_in_order",
        Bool(),
        Ite(
            Eq(list_length(data), IntLit(0)),
            BoolLit(True),
            Call(
                "ops_in_order_helper",
                Bool(),
                list_get(data, IntLit(0)),
                list_tail(data, IntLit(1)),
            ),
        ),
        data,
    )

    return [reduce_fn, ops_in_order_helper, ops_in_order]


class SynthesizeFun(Protocol):
    def __call__(
        self,
        basename: str,
        targetLang: typing.List[Union[FnDecl, FnDeclNonRecursive, Axiom]],
        vars: typing.Set[Var],
        invAndPs: typing.List[Synth],
        preds: Union[str, typing.List[Expr]],
        vc: Expr,
        loopAndPsInfo: typing.List[Union[CodeInfo, Expr]],
        cvcPath: str = "cvc5",
        uid: int = 0,
        noVerify: bool = False,
        unboundedInts: bool = False,
        optimize_vc_equality: bool = False,
        listBound: int = 2,
    ) -> typing.List[FnDecl]:
        ...


def synthesize_actor(
    filename: str,
    fnNameBase: str,
    loopsFile: str,
    cvcPath: str,
    synthStateType: Type,
    initState: Callable[[], Expr],
    grammarStateInvariant: Callable[[Expr, int], Expr],
    grammarSupportedCommand: Callable[[Expr, typing.Any, int], Expr],
    inOrder: Callable[[typing.Any, typing.Any], Expr],
    opPrecondition: Callable[[typing.Any], Expr],
    grammar: Callable[[CodeInfo], Synth],
    grammarQuery: Callable[[CodeInfo], Synth],
    grammarEquivalence: Callable[[Expr, Expr, typing.List[Var]], Expr],
    targetLang: Callable[[], typing.List[Union[FnDecl, FnDeclNonRecursive, Axiom]]],
    synthesize: SynthesizeFun,
    stateTypeHint: typing.Optional[Type] = None,
    opArgTypeHint: typing.Optional[typing.List[Type]] = None,
    queryArgTypeHint: typing.Optional[typing.List[Type]] = None,
    queryRetTypeHint: typing.Optional[Type] = None,
    uid: int = 0,
    unboundedInts: bool = True,
    useOpList: bool = False,
    listBound: int = 1,
    invariantBoost: int = 0,
    log: bool = True,
    skipSynth: bool = False,
) -> typing.List[FnDecl]:
    basename = os.path.splitext(os.path.basename(filename))[0]
    origSynthStateType = synthStateType

    opType: Type = None  # type: ignore

    def supportedCommandWithList(synthState: Expr, args: typing.Any) -> Expr:
        return And(
            opPrecondition(args),
            Ite(
                Eq(
                    Call(
                        "list_length",
                        Int(),
                        TupleGet(synthState, IntLit(len(synthStateType.args) - 1)),
                    ),
                    IntLit(0),
                ),
                BoolLit(True),
                inOrder(
                    unpackOp(
                        Call(
                            "list_get",
                            opType,
                            TupleGet(synthState, IntLit(len(synthStateType.args) - 1)),
                            IntLit(0),
                        )
                    ),
                    args,
                ),
            ),
        )

    # analyze query just to grab the query parameters
    queryParameterTypes = []
    beforeOrigState: Expr = None  # type: ignore
    beforeSynthState: Expr = None  # type: ignore
    extraVarsStateQuery: typing.Set[Var] = set()
    queryArgs: typing.List[Var] = None  # type: ignore

    mode = "before_state"

    def extractQueryParameters(ps: MLInst) -> typing.Tuple[Expr, typing.List[Expr]]:
        nonlocal queryParameterTypes
        nonlocal beforeOrigState
        nonlocal beforeSynthState
        nonlocal queryArgs

        if queryArgTypeHint:
            queryParameterTypes = queryArgTypeHint
        else:
            queryParameterTypes = [parseTypeRef(v.type) for v in ps.operands[4:]]  # type: ignore

        origReturn = ps.operands[2]
        origArgs = ps.operands[3:]

        beforeState = typing.cast(ValueRef, origArgs[0])
        beforeOrigState = Var(
            beforeState.name + f"_orig_for_{mode}_query", parseTypeRef(beforeState.type)
        )
        extraVarsStateQuery.add(beforeOrigState)

        beforeSynthState = Var(beforeState.name + f"_for_{mode}_query", synthStateType)
        extraVarsStateQuery.add(beforeSynthState)

        queryArgs = [Var(v.name + f"_for_{mode}_query", parseTypeRef(v.type)) for v in origArgs[1:]]  # type: ignore
        for q in queryArgs:
            extraVarsStateQuery.add(q)

        newArgs = list(origArgs)
        newArgs[0] = beforeSynthState

        same_check = Eq(origReturn, Call(f"{fnNameBase}_response", origReturn.type, *newArgs))  # type: ignore

        return (
            Implies(
                And(
                    Eq(beforeState, beforeOrigState),
                    *[
                        Eq(a, qa)  # type: ignore
                        for a, qa in zip(origArgs[1:], queryArgs)
                    ],
                ),
                Implies(same_check, Var("to_be_replaced_before_state", Bool()))
                if mode == "before_state"
                else same_check,
            ),
            [origReturn] + newArgs,
        )

    (vcVarsBeforeStateQuery, _, _, vcBeforeStateQuery, _,) = analyze(
        filename,
        fnNameBase + "_response",
        loopsFile,
        wrapSummaryCheck=extractQueryParameters,
        fnNameSuffix=f"_{mode}_query",
        log=False,
    )

    beforeOrigStateCopy = beforeOrigState
    beforeSynthStateCopy = beforeSynthState
    beforeQueryArgs = queryArgs

    mode = "after_state"

    (vcVarsAfterStateQuery, _, _, vcAfterStateQuery, _,) = analyze(
        filename,
        fnNameBase + "_response",
        loopsFile,
        wrapSummaryCheck=extractQueryParameters,
        fnNameSuffix=f"_{mode}_query",
        log=False,
    )

    afterOrigState = beforeOrigState
    afterSynthState = beforeSynthState
    afterQueryArgs = queryArgs

    mode = "init_state"

    (vcVarsInitStateQuery, _, _, vcInitStateQuery, _,) = analyze(
        filename,
        fnNameBase + "_response",
        loopsFile,
        wrapSummaryCheck=extractQueryParameters,
        fnNameSuffix=f"_{mode}_query",
        log=False,
    )

    initStateOrigState = beforeOrigState
    initStateSynthState = beforeSynthState
    initStateQueryArgs = queryArgs

    beforeOrigState = beforeOrigStateCopy
    beforeSynthState = beforeSynthStateCopy
    # end query param extraction

    # begin state transition (in order)
    stateTypeOrig: Type = None  # type: ignore
    stateTransitionArgs: typing.List[Var] = []
    op_arg_types: typing.List[Type] = []

    extraVarsStateTransition: typing.Set[Var] = set()

    def summaryWrapStateTransition(
        ps: MLInst,
    ) -> typing.Tuple[Expr, typing.List[Expr]]:
        nonlocal stateTypeOrig
        nonlocal stateTransitionArgs
        nonlocal op_arg_types
        nonlocal opType
        nonlocal synthStateType

        origReturn = ps.operands[2]
        origArgs = ps.operands[3:]

        for i in range(len(origArgs) - 1):
            op_arg_types.append(parseTypeRef(origArgs[i + 1].type))  # type: ignore
        opType = TupleT(*op_arg_types) if len(op_arg_types) > 1 else op_arg_types[0]
        if useOpList:
            synthStateType = TupleT(*synthStateType.args, List(opType))
            beforeSynthState.type = synthStateType
            afterSynthState.type = synthStateType
            initStateSynthState.type = synthStateType

        stateTransitionArgs = [
            Var(f"state_transition_arg_{i}", parseTypeRef(origArgs[i + 1].type))  # type: ignore
            for i in range(len(origArgs) - 1)
        ]
        for arg in stateTransitionArgs:
            extraVarsStateTransition.add(arg)

        beforeStateOrig = typing.cast(ValueRef, origArgs[0])
        afterStateOrig = typing.cast(ValueRef, origReturn)

        stateTypeOrig = parseTypeRef(beforeStateOrig.type)

        beforeStateForPS = Var(
            beforeStateOrig.name + "_for_state_transition", synthStateType
        )
        extraVarsStateTransition.add(beforeStateForPS)

        afterStateForPS = Var(
            afterStateOrig.name + "_for_state_transition", synthStateType
        )
        extraVarsStateTransition.add(afterStateForPS)

        queryParamVars = [
            Var(f"state_transition_query_param_{i}", queryParameterTypes[i])
            for i in range(len(queryParameterTypes))
        ]
        for v in queryParamVars:
            extraVarsStateTransition.add(v)

        newReturn = afterStateForPS

        newArgs = list(origArgs)
        newArgs[0] = beforeStateForPS

        return (
            Implies(
                And(
                    observeEquivalence(
                        beforeStateOrig, beforeStateForPS, queryParamVars
                    ),
                    And(
                        Eq(beforeStateOrig, beforeOrigState),
                        Eq(beforeStateForPS, beforeSynthState),
                        *[
                            Eq(a1, a2)
                            for a1, a2 in zip(queryParamVars, beforeQueryArgs)
                        ],
                    ),
                    *(
                        [
                            opsListInvariant(
                                fnNameBase, beforeStateForPS, synthStateType, opType
                            ),
                            supportedCommandWithList(beforeStateForPS, origArgs[1:]),
                        ]
                        if useOpList
                        else [
                            opPrecondition(origArgs[1:]),
                            supportedCommand(beforeStateForPS, origArgs[1:]),
                        ]
                    ),
                    Eq(newReturn, Call(f"{fnNameBase}_next_state", newReturn.type, *newArgs)),  # type: ignore
                ),
                vcBeforeStateQuery.rewrite(
                    {
                        "to_be_replaced_before_state": And(
                            observeEquivalence(
                                afterStateOrig, afterStateForPS, queryParamVars
                            ),
                            Implies(
                                And(
                                    Eq(afterStateOrig, afterOrigState),
                                    Eq(afterStateForPS, afterSynthState),
                                    *[
                                        Eq(a1, a2)
                                        for a1, a2 in zip(
                                            queryParamVars, afterQueryArgs
                                        )
                                    ],
                                ),
                                vcAfterStateQuery,
                            ),
                            *(
                                [
                                    Implies(
                                        And(
                                            inOrder(origArgs[1:], stateTransitionArgs),
                                            opPrecondition(stateTransitionArgs),
                                        ),
                                        supportedCommand(
                                            afterStateForPS, stateTransitionArgs
                                        ),
                                    )
                                ]
                                if not useOpList
                                else []
                            ),
                        ),
                    }
                ),
            ),
            [newReturn] + newArgs,  # type: ignore
        )

    (
        vcVarsStateTransition,
        invAndPsStateTransition,
        predsStateTransition,
        vcStateTransition,
        loopAndPsInfoStateTransition,
    ) = analyze(
        filename,
        fnNameBase + "_next_state",
        loopsFile,
        wrapSummaryCheck=summaryWrapStateTransition,
        fnNameSuffix="_state_transition",
        log=log,
    )

    vcVarsStateTransition = vcVarsStateTransition.union(extraVarsStateTransition).union(
        vcVarsBeforeStateQuery.union(vcVarsAfterStateQuery).union(extraVarsStateQuery)
    )

    if opArgTypeHint:
        for i in range(len(opArgTypeHint)):
            loopAndPsInfoStateTransition[0].readVars[i + 1].my_type = opArgTypeHint[i]  # type: ignore

    loopAndPsInfoStateTransition[0].retT = (
        loopAndPsInfoStateTransition[0].modifiedVars[0].type
    )
    loopAndPsInfoStateTransition[0].modifiedVars = []

    stateTransitionSynthNode = grammar(loopAndPsInfoStateTransition[0])

    invAndPsStateTransition = (
        [
            Synth(
                stateTransitionSynthNode.args[0],
                Tuple(
                    *stateTransitionSynthNode.args[1].args,
                    Call(
                        "list_prepend",
                        List(opType),
                        Tuple(*loopAndPsInfoStateTransition[0].readVars[1:])
                        if len(loopAndPsInfoStateTransition[0].readVars[1:]) > 1
                        else loopAndPsInfoStateTransition[0].readVars[1],
                        TupleGet(
                            typing.cast(
                                Expr, loopAndPsInfoStateTransition[0].readVars[0]
                            ),
                            IntLit(len(synthStateType.args) - 1),
                        ),
                    ),
                ),
                *stateTransitionSynthNode.args[2:],
            )
        ]
        if useOpList
        else [stateTransitionSynthNode]
    )
    # end state transition (in order)

    # begin query
    def summaryWrapQuery(ps: MLInst) -> typing.Tuple[Expr, typing.List[Expr]]:
        origReturn = ps.operands[2]
        origArgs = ps.operands[3:]

        beforeState = typing.cast(ValueRef, origArgs[0])

        beforeStateForQuery = Var(beforeState.name + "_for_query", synthStateType)

        newArgs = list(origArgs)
        newArgs[0] = beforeStateForQuery

        # unused, but summary wrap needed to swap in synth state argument
        return (
            ps,  # type: ignore
            [origReturn] + newArgs,
        )

    (_, invAndPsQuery, predsQuery, _, loopAndPsInfoQuery) = analyze(
        filename,
        fnNameBase + "_response",
        loopsFile,
        wrapSummaryCheck=summaryWrapQuery,
        log=log,
    )

    if queryArgTypeHint:
        for i in range(len(queryArgTypeHint)):
            loopAndPsInfoQuery[0].readVars[i + 1].my_type = queryArgTypeHint[i]  # type: ignore

    loopAndPsInfoQuery[0].retT = (
        loopAndPsInfoQuery[0].modifiedVars[0].type  # type: ignore
        if queryRetTypeHint == None
        else queryRetTypeHint
    )
    loopAndPsInfoQuery[0].modifiedVars = []
    invAndPsQuery = [grammarQuery(ci) for ci in loopAndPsInfoQuery]
    # end query

    # begin init state
    extraVarsInitState = set()

    synthInitState = Var("synth_init_state", synthStateType)

    extraVarsInitState.add(synthInitState)

    init_op_arg_vars = []
    for i, typ in enumerate(op_arg_types):
        init_op_arg_vars.append(Var(f"init_op_arg_{i}", typ))
        extraVarsInitState.add(init_op_arg_vars[-1])

    def summaryWrapInitState(ps: MLInst) -> typing.Tuple[Expr, typing.List[Expr]]:
        origReturn = ps.operands[2]

        returnedInitState = typing.cast(ValueRef, origReturn)

        queryParamVars = [
            Var(f"init_state_equivalence_query_param_{i}", queryParameterTypes[i])
            for i in range(len(queryParameterTypes))
        ]
        for v in queryParamVars:
            extraVarsInitState.add(v)

        return (
            Implies(
                And(
                    Eq(
                        synthInitState,
                        Call(f"{fnNameBase}_init_state", synthStateType),
                    )
                ),
                And(
                    observeEquivalence(
                        returnedInitState, synthInitState, queryParamVars
                    ),
                    Implies(
                        And(
                            Eq(returnedInitState, initStateOrigState),
                            Eq(synthInitState, initStateSynthState),
                            *[
                                Eq(a1, a2)
                                for a1, a2 in zip(queryParamVars, initStateQueryArgs)
                            ],
                        ),
                        vcInitStateQuery,
                    ),
                    opsListInvariant(fnNameBase, synthInitState, synthStateType, opType)
                    if useOpList
                    else Implies(
                        opPrecondition(init_op_arg_vars),
                        supportedCommand(synthInitState, init_op_arg_vars),
                    ),
                ),
            ),
            list(ps.operands[2:]),  # type: ignore
        )

    (
        vcVarsInitState,
        invAndPsInitState,
        predsInitState,
        vcInitState,
        loopAndPsInfoInitState,
    ) = analyze(
        filename,
        fnNameBase + "_init_state",
        loopsFile,
        wrapSummaryCheck=summaryWrapInitState,
        log=log,
    )

    vcVarsInitState = vcVarsInitState.union(extraVarsInitState).union(
        vcVarsInitStateQuery
    )
    loopAndPsInfoInitState[0].retT = loopAndPsInfoInitState[0].modifiedVars[0].type
    loopAndPsInfoInitState[0].modifiedVars = []
    initStateSynthNode = initState()
    invAndPsInitState = [
        Synth(
            fnNameBase + "_init_state",
            Tuple(
                *initStateSynthNode.args,
                Call("list_empty", List(opType)),
            )
            if useOpList
            else Tuple(
                *initStateSynthNode.args,
            ),
        )
    ]
    # end init state

    # begin equivalence
    inputStateForEquivalence = Var(
        "inputState", stateTypeOrig if stateTypeHint == None else stateTypeHint  # type: ignore
    )
    synthStateForEquivalence = Var("synthState", synthStateType)

    equivalenceQueryParams = [
        Var(f"equivalence_query_param_{i}", queryParameterTypes[i])
        for i in range(len(queryParameterTypes))
    ]

    invAndPsEquivalence = [
        Synth(
            "equivalence",
            And(
                grammarEquivalence(
                    inputStateForEquivalence,
                    synthStateForEquivalence,
                    equivalenceQueryParams,
                ),
                *(
                    [grammarStateInvariant(synthStateForEquivalence, invariantBoost)]
                    if not useOpList
                    else []
                ),
            ),
            inputStateForEquivalence,
            synthStateForEquivalence,
            *equivalenceQueryParams,
        )
    ]

    synthStateForSupported = Var(f"supported_synthState", synthStateType)
    argList = [
        Var(
            f"supported_arg_{i}",
            stateTransitionArgs[i].type
            if (opArgTypeHint == None)
            else opArgTypeHint[i],  # type: ignore
        )
        for i in range(len(stateTransitionArgs))
    ]
    invAndPsSupported = (
        [
            Synth(
                "supportedCommand",
                grammarSupportedCommand(
                    synthStateForSupported, argList, invariantBoost
                ),
                synthStateForSupported,
                *argList,
            )
        ]
        if not useOpList
        else []
    )
    # end equivalence

    if log:
        print("====== synthesis")

    combinedVCVars = vcVarsStateTransition.union(vcVarsInitState)

    combinedInvAndPs = (
        invAndPsStateTransition
        + invAndPsQuery
        + invAndPsInitState
        + invAndPsEquivalence
        + invAndPsSupported
    )

    combinedPreds = predsStateTransition + predsInitState + predsQuery

    combinedLoopAndPsInfo: typing.List[Union[CodeInfo, Expr]] = (
        loopAndPsInfoStateTransition
        + loopAndPsInfoQuery
        + loopAndPsInfoInitState
        + invAndPsEquivalence  # type: ignore
        + invAndPsSupported  # type: ignore
    )
    combinedVC = And(vcStateTransition, vcInitState)

    lang = targetLang()
    if useOpList:
        lang = lang + opListAdditionalFns(
            synthStateType, opType, initState, inOrder, opPrecondition
        )

    if skipSynth:
        return  # type: ignore

    try:
        out = synthesize(
            basename,
            lang,
            combinedVCVars,
            combinedInvAndPs,
            combinedPreds,
            combinedVC,
            combinedLoopAndPsInfo,
            cvcPath,
            uid=uid,
            unboundedInts=unboundedInts,
            noVerify=useOpList,
            listBound=listBound,
        )
    except VerificationFailed:
        print("INCREASING LIST BOUND TO", listBound + 1)
        return synthesize_actor(
            filename,
            fnNameBase,
            loopsFile,
            cvcPath,
            origSynthStateType,
            initState,
            grammarStateInvariant,
            grammarSupportedCommand,
            inOrder,
            opPrecondition,
            grammar,
            grammarQuery,
            grammarEquivalence,
            targetLang,
            synthesize,
            stateTypeHint=stateTypeHint,
            opArgTypeHint=opArgTypeHint,
            queryArgTypeHint=queryArgTypeHint,
            queryRetTypeHint=queryRetTypeHint,
            uid=uid,
            unboundedInts=unboundedInts,
            useOpList=useOpList,
            listBound=listBound + 1,
            invariantBoost=invariantBoost,
            log=log,
        )

    if useOpList:
        print(
            f"{uid}: Re-synthesizing to identify invariants (list bound: {listBound})"
        )
        equivalence_fn = [x for x in out if x.args[0] == "equivalence"][0]
        state_transition_fn = [
            x for x in out if x.args[0] == f"{fnNameBase}_next_state"
        ][0]
        query_fn = [x for x in out if x.args[0] == f"{fnNameBase}_response"][0]
        init_state_fn = [x for x in out if x.args[0] == f"{fnNameBase}_init_state"][0]

        equivalence_fn.args[3] = Var(
            equivalence_fn.args[3].args[0],
            TupleT(*equivalence_fn.args[3].type.args[:-1]),
        )

        equivalence_fn.args[1] = equivalence_fn.args[1].rewrite(
            {equivalence_fn.args[3].args[0]: equivalence_fn.args[3]}
        )

        state_transition_fn.args[2] = Var(
            state_transition_fn.args[2].args[0],
            TupleT(*state_transition_fn.args[2].type.args[:-1]),
        )

        state_transition_fn.args[1] = Tuple(
            *[
                e.rewrite(
                    {state_transition_fn.args[2].args[0]: state_transition_fn.args[2]}
                )
                for e in state_transition_fn.args[1].args[:-1]
            ]
        )

        query_fn.args[2] = Var(
            query_fn.args[2].args[0], TupleT(*query_fn.args[2].type.args[:-1])
        )

        query_fn.args[1] = query_fn.args[1].rewrite(
            {query_fn.args[2].args[0]: query_fn.args[2]}
        )

        init_state_fn.args[1] = Tuple(*init_state_fn.args[1].args[:-1])

        try:
            return synthesize_actor(
                filename,
                fnNameBase,
                loopsFile,
                cvcPath,
                origSynthStateType,
                lambda: init_state_fn.args[1],  # type: ignore
                grammarStateInvariant,
                grammarSupportedCommand,
                inOrder,
                opPrecondition,
                lambda _: Synth(
                    state_transition_fn.args[0],
                    state_transition_fn.args[1],
                    *state_transition_fn.args[2:],
                ),
                lambda _: Synth(query_fn.args[0], query_fn.args[1], *query_fn.args[2:]),
                lambda a, b, c: equivalence_fn.args[1],  # type: ignore
                targetLang,
                synthesize,
                stateTypeHint=stateTypeHint,
                opArgTypeHint=opArgTypeHint,
                queryArgTypeHint=queryArgTypeHint,
                queryRetTypeHint=queryRetTypeHint,
                uid=uid,
                unboundedInts=unboundedInts,
                useOpList=False,
                listBound=listBound,
                invariantBoost=invariantBoost,
                log=log,
            )
        except SynthesisFailed:
            try:
                # try to re-verify with a larger bound
                print(f"{uid}: RE-VERIFYING WITH LIST BOUND TO", listBound + 1)
                return synthesize_actor(
                    filename,
                    fnNameBase,
                    loopsFile,
                    cvcPath,
                    origSynthStateType,
                    lambda: init_state_fn.args[1],  # type: ignore
                    grammarStateInvariant,
                    grammarSupportedCommand,
                    inOrder,
                    opPrecondition,
                    lambda ci: Synth(
                        state_transition_fn.args[0],
                        state_transition_fn.args[1],
                        *ci.modifiedVars,
                        *ci.readVars,
                    ),
                    lambda ci: Synth(query_fn.args[0], query_fn.args[1], *ci.readVars),
                    lambda a, b, c: equivalence_fn.args[1],  # type: ignore
                    targetLang,
                    synthesize,
                    stateTypeHint=stateTypeHint,
                    opArgTypeHint=opArgTypeHint,
                    queryArgTypeHint=queryArgTypeHint,
                    queryRetTypeHint=queryRetTypeHint,
                    uid=uid,
                    unboundedInts=unboundedInts,
                    useOpList=useOpList,
                    listBound=listBound + 1,
                    invariantBoost=invariantBoost + 1,
                    log=log,
                )
            except SynthesisFailed:
                print(f"{uid}: INCREASING LIST BOUND TO", listBound + 1)
                return synthesize_actor(
                    filename,
                    fnNameBase,
                    loopsFile,
                    cvcPath,
                    origSynthStateType,
                    initState,
                    grammarStateInvariant,
                    grammarSupportedCommand,
                    inOrder,
                    opPrecondition,
                    grammar,
                    grammarQuery,
                    grammarEquivalence,
                    targetLang,
                    synthesize,
                    stateTypeHint=stateTypeHint,
                    opArgTypeHint=opArgTypeHint,
                    queryArgTypeHint=queryArgTypeHint,
                    queryRetTypeHint=queryRetTypeHint,
                    uid=uid,
                    unboundedInts=unboundedInts,
                    useOpList=useOpList,
                    listBound=listBound + 1,
                    invariantBoost=invariantBoost,
                    log=log,
                )
    else:
        return out
