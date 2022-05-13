import os
import sys

from metalift.analysis import CodeInfo, analyze
from metalift.ir import *
from metalift.rosette_translator import toRosette
from metalift.smt_util import toSMT

from metalift.synthesize_auto import synthesize


def l2_norm(x: Var, y: Var):
    return Call("l2_norm", Int(), x, y)


def grammar(ci: CodeInfo):
    name = ci.name
    if name.startswith("inv"):
        raise Exception("no invariant")
    else:  # ps
        r = ci.modifiedVars[0]
        (x, y) = ci.readVars
        summary = Choose(
            Eq(r, l2_norm(x, y)), 
            Eq(r, Add(x, y)),
            Eq(r, Add(Mul(x, y), Mul(x, y))),
            Eq(r, Add(1, Add(Mul(x, x), Mul(y, y))))
        )
        return Synth(name, summary, *ci.modifiedVars, *ci.readVars)

def targetLang():
    x = Var("x", Int())
    y = Var("y", Int())
    l2_norm = FnDecl("l2_norm", Int(), Add(Mul(x, x), Mul(y, y)), x, y)
    return [l2_norm]


if __name__ == "__main__":
    filename = "tests/l2_norm.ll"
    basename = "l2_norm"

    fnName = "_Z4testii"
    loopsFile = "tests/l2_norm.loops"
    cvcPath = "/Users/tommyjoseph/desktop/deps-metalift/cvc5-macOS"

    (vars, invAndPs, preds, vc, loopAndPsInfo) = analyze(filename, fnName, loopsFile)

    print("====== synthesis")
    invAndPs = [grammar(ci) for ci in loopAndPsInfo]

    lang = targetLang()

    candidates = synthesize(
        basename,
        lang,
        vars,
        invAndPs,
        preds,
        vc,
        loopAndPsInfo,
        cvcPath,
    )

    print("====== verified candidates")
    for c in candidates:
        print(c, "\n")
