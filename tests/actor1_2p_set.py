from email.mime import base
from metalift.actors.search_structures import search_crdt_structures
from metalift.analysis import CodeInfo
from metalift.ir import *
from metalift.actors.synthesis import synthesize_actor
from metalift.actors.aci import check_aci
import metalift.actors.lattices as lat
from metalift.actors.auto_grammar import auto_grammar
import sys
from metalift.maps_lang import mapsLang

from metalift.synthesize_auto import synthesize

base_depth = 1

def grammarEquivalence(inputState, synthState, queryParams):
    return auto_grammar(
        Bool(),
        base_depth,
        inputState, synthState, *queryParams
    )


def grammarStateInvariant(synthState, synthStateStructure):
    return auto_grammar(Bool(), base_depth, synthState)


def grammarSupportedCommand(synthState, args, synthStateStructure):
    conditions = [Eq(args[0], IntLit(1))]

    out = auto_grammar(Bool(), base_depth, synthState, *args[1:])
    for c in conditions:
        out = Ite(c, out, out)

    return out


def inOrder(arg1, arg2):
    # removes win
    return Ite(
        Eq(arg1[0], IntLit(1)),  # if first command is insert
        BoolLit(True),  # second can be insert or remove
        Not(Eq(arg2[0], IntLit(1))),  # but if remove, must be remove next
    )


def grammarQuery(ci: CodeInfo):
    name = ci.name

    setContainTransformed = auto_grammar(Bool(), base_depth + 1, *ci.readVars)

    summary = Ite(setContainTransformed, IntLit(1), IntLit(0))

    return Synth(name, summary, *ci.readVars)


def grammar(ci: CodeInfo, synthStateStructure):
    name = ci.name

    if name.startswith("inv"):
        raise Exception("no invariant")
    else:  # ps
        inputState = ci.readVars[0]
        args = ci.readVars[1:]

        conditions = [Eq(args[0], IntLit(1))]
        def fold_conditions(out):
            for c in conditions:
                out = Ite(c, out, out)
            return out

        out = Tuple(
            *[
                synthStateStructure[i].merge(
                    TupleGet(inputState, IntLit(i)),
                    fold_conditions(auto_grammar(TupleGet(inputState, IntLit(i)).type, base_depth, *args[1:]))
                )
                for i in range(len(synthStateStructure))
            ],
        )

        return Synth(name, out, *ci.modifiedVars, *ci.readVars)


def initState(synthStateStructure):
    return Tuple(
        *[elem.bottom() for elem in synthStateStructure]
    )

def targetLang():
    return mapsLang()


if __name__ == "__main__":
    mode = sys.argv[1]
    filename = "tests/actor1.ll"
    fnNameBase = "test"
    loopsFile = "tests/actor1.loops"
    cvcPath = "cvc5"

    if mode == "aci":
        check_aci(
            filename,
            fnNameBase,
            loopsFile,
            cvcPath,
        )
    else:
        useOpList = False
        if mode == "synth-oplist":
            useOpList = True

        search_crdt_structures(
            initState,
            grammarStateInvariant,
            grammarSupportedCommand,
            inOrder,
            lambda _: BoolLit(True),
            grammar,
            grammarQuery,
            grammarEquivalence,
            targetLang,
            synthesize,
            filename, fnNameBase, loopsFile, cvcPath, useOpList,
            lat.gen_structures(),
            stateTypeHint=Set(OpaqueInt()),
            opArgTypeHint=[BoolInt(), OpaqueInt()],
            queryArgTypeHint=[OpaqueInt()],
        )
