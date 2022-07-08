{ config, lib, pkgs, ...}: {
  imports = [
    # "${nixpkgs}/nixos/modules/installer/cd-dvd/iso-image.nix"
  ];

  environment.systemPackages = with pkgs; [
    (poetry2nix.mkPoetryEnv {
      projectDir = ./.;
      preferWheels = true;
    })

    cvc5
    gnumake
    cmake
    llvm_11
    llvm_11.dev
    clang_11

    racket # PKGS="rosette"
  ];

  users = {
    mutableUsers = false;
    allowNoPasswordLogin = true;

    users = {
      demo = {
        hashedPassword = "*";
        home = "/home/demo";
        extraGroups = [ "wheel" ];
        isNormalUser = true;
      };
    };
  };

  security.sudo.wheelNeedsPassword = false;

  boot.postBootCommands = ''
    rm -rf /home/demo
    ${pkgs.rsync}/bin/rsync -r --owner --group --chown=demo:users --perms --chmod=u+rw /iso/demo /home
    mkdir /home/demo/.racket/8.5/pkgs/rosette/bin
    ln -s ${pkgs.z3}/bin/z3 /home/demo/.racket/8.5/pkgs/rosette/bin/z3
  '';

  services.getty.autologinUser = "demo";

  isoImage.contents = [ {
    source = let
      gitignoreSrc = pkgs.fetchFromGitHub { 
        owner = "hercules-ci";
        repo = "gitignore.nix";
        # put the latest commit sha of gitignore Nix library here:
        rev = "bff2832ec341cf30acb3a4d3e2e7f1f7b590116a";
        # use what nix suggests in the mismatch message here:
        hash = "sha256-kekOlTlu45vuK2L9nq8iVN17V3sB0WWPqTTW3a2SQG0=";
      };
      inherit (import gitignoreSrc { inherit (pkgs) lib; }) gitignoreSource;
    in gitignoreSource ./.;
    target = "/demo";
  } {
    # raco pkg install --scope-dir rosette-packages rosette
    source = ./rosette-packages;
    target = "/demo/.racket/8.5/pkgs";
  } {
    source = ./iso-racket-links.rktd;
    target = "/demo/.racket/8.5/links.rktd";
  } ];
}
