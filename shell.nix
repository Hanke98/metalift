let
  pkgs = import <nixpkgs> {};
  unstable = import <nixos-unstable> {};
in
with pkgs;

let
  cvc5 = callPackage ./cvc5.nix { unstable = unstable; };
in
mkShell {
  venvDir = "./.venv";
  buildInputs = [
    (python38.withPackages (p: with p; [
      pyparsing
      black
      mypy
    ]))

    cvc5
    llvm_11
    clang_11
    cmake
  ];

  hardeningDisable = [ "fortify" ];

  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    stdenv.cc.cc
  ];

  NIX_LD = lib.fileContents "${stdenv.cc}/nix-support/dynamic-linker";

  PYTHONPATH="llvmlite";
}
