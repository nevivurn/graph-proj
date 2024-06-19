{
  mkShell,
  pandoc,
  texliveSmall,
  python3,
}:

mkShell {
  nativeBuildInputs = [
    (python3.withPackages (
      ps: with ps; [
        numba
        pillow
        scipy
      ]
    ))
    pandoc
    texliveSmall
    python3.pkgs.flake8
  ];
}
