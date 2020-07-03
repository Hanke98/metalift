### Steps to run code

1. install LLVM, [Rosette](https://emina.github.io/rosette/), and [Serval](https://github.com/uw-unsat/serval). 
   Make sure you run the package installers with `raco`.

2. compile benchmarks and target in `tests/basic` to LLVM bytecode <br />
   `clang -O0 -c benchmarks.c -S -emit-llvm -o benchmarks.ll` <br />
   `clang -O0 -c target.c -S -emit-llvm -o target.ll`

3. run serval to translate to LLVM bytecode to serval's interpreter instructions <br />
   `racket <serval dir>/bin/serval-llvm.rkt < benchmarks.ll > benchmarks.ll.rkt` <br />
   `racket <serval dir>/bin/serval-llvm.rkt < target.ll > target.ll.rkt` <br />
   Notice that serval translates in two steps: it first translates LLVM bytecode into
   its own Racket IR (output of `bytes->module`), and then converts each AST into
   instructions for its own symbolic interpreter (output of `print-module`) and prints them out.

4. run our interpreter `compiler.rkt`. You should be able to see the translated output


### Synthesis algorithms to (re-)implement

* type-driven synthesis in [QBS](https://homes.cs.washington.edu/~akcheung/papers/pldi13.pdf)
* incremental synthesis in [Casper](http://casper.uwplse.org/)
* symbolic execution driven synthesis in [STNG](http://stng.uwplse.org/)
* multi-stage synthesis in [Dexter](http://dexter.uwplse.org/)
* (TBD)


### TODOs

* run LLVM's loop identification pass to label loops. Do so with `opt benchmarks.ll -loops -analyze -S`

* remove loops from LLVM bytecode output. See [this](https://courses.cs.washington.edu/courses/cse507/19au/doc/L13.pdf). 
  Maybe easiest to implement this on the output of serval's `bytes->module`?

* modify serval's symbolic interpreter to keep track of the assertions generated

* modify `compiler.rkt` to gather the assertions from serval interpreter, and call generator function to come up with invariants and postconditions

* translate the verified assertions to SMTLIB for formal verification
