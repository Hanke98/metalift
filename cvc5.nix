{ pkgs, unstable }:
with pkgs;

let
  symfpu = stdenv.mkDerivation rec {
    pname = "symfpu";
    version = "8fbe139bf0071cbe0758d2f6690a546c69ff0053";
    
    src = fetchFromGitHub {
      owner  = "martin-cs";
      repo   = "symfpu";
      rev    = version;
      sha256 = "1jf5lkn67q136ppfacw3lsry369v7mdr1rhidzjpbz18jfy9zl9q";
    };

    installPhase = ''
      mkdir -p $out
      mkdir -p $out/symfpu
      cp -r * $out/symfpu/
    '';
  };
in
stdenv.mkDerivation rec {
  pname = "cvc5";
  version = "cvc5-0.0.3";

  src = fetchFromGitHub {
    owner  = "cvc5";
    repo   = "cvc5";
    rev    = version;
    sha256 = "1l1n2d5sxxp2vv0n5j70lvmj4mcfda4wippnl7mm22xb10a2gn9c";
  };

  nativeBuildInputs = [ pkg-config cmake ];
  buildInputs = [ gmp git python3.pkgs.toml gtest libantlr3c antlr3_4 boost jdk python3 ];

  preConfigure = ''
    patchShebangs ./src/
  '';

  cmakeFlags = [
    "-DCMAKE_BUILD_TYPE=Production"
    "-DCaDiCaL_INCLUDE_DIR=${unstable.cadical.dev}/include/"
    "-DCaDiCaL_LIBRARIES=${unstable.cadical.lib}/lib/libcadical.a"
    "-DCaDiCaL_FOUND=1"
    "-DANTLR3_JAR=${antlr3_4}/lib/antlr/antlr-3.4-complete.jar"
    "-DSymFPU_INCLUDE_DIR=${(symfpu)}"
  ];
}
