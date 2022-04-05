import os
import sys
from ir import *
from analysis import CodeInfo, analyze

from rosette_translator import toRosette
from smt_util import toSMT
from synthesize_rosette import synthesize





def grammar(ci: CodeInfo):
    name = ci.name
    nested =  False
    if name.startswith("inv"):
        mv = ci.modifiedVars
        rv = ci.readVars
        summary = Choose(ci.modifiedVars[0])
        return Synth(ci.name, summary, *ci.modifiedVars, *ci.readVars)

    else:
        mv = ci.modifiedVars[0]
        summary = Choose(ci.readVars[0])
        
        return Synth(name, summary, *ci.modifiedVars, *ci.readVars)



if __name__ == "__main__":

    filename = "tests/reset_field1.ll"
    basename = "reset_field1"

    fnName = "_Z4testP4listIiES1_iiii"
    loopsFile = "tests/reset_field1.loops"
    cvcPath = sys.argv[1]

    (vars, invAndPs, preds, vc, loopAndPsInfo) = analyze(filename, fnName, loopsFile)

    print("====== synthesis")

    invAndPs = [grammar(ci) for ci in loopAndPsInfo]

    print("====== VC")
    print(vc.toRosette())

    # candidates = synthesize(
    #     basename,
    #     lang,
    #     vars,
    #     invAndPs + fnsGrammar,
    #     preds,
    #     vc,
    #     loopAndPsInfo,
    #     cvcPath,
    #     noVerify=False,
    #     unboundedInts=True
    # )
