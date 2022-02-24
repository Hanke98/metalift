import os
import sys

from analysis import CodeInfo, analyze
from ir import *
from rosette_translator import toRosette
from smt_util import toSMT
from synthesize_rosette import synthesize


def double(t):
    return Call("double", Int(), t)


def grammar(ci: CodeInfo):
    name = ci.name

    if name.startswith("inv"):
        raise Exception("no invariant")
    else:  # ps
        outputVar = ci.modifiedVars[0]
        readVar = Choose(*ci.readVars)
        summary = Choose(
            Eq(outputVar, Add(double(readVar), double(readVar))),
            Eq(outputVar, Sub(double(readVar), double(readVar))),
        )
        return Synth(name, summary, *ci.modifiedVars, *ci.readVars)


def targetLang():
    x = Var("x", Int())
    double = FnDecl("double", Int(), Add(x, x), x)
    return [double]


if __name__ == "__main__":
    filename = "tests/maps1.ll"
    basename = "maps1"

    fnName = "_Z4testii"
    loopsFile = "tests/maps1.loops"

    cvcPath = "cvc5"

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
        noVerify=False,
    )

    print("====== verified candidates")
    for c in candidates:
        print(c.toSMT(), "\n")

    