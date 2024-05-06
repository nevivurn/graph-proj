{ mkShell, pandoc, texliveSmall, python3 }:

mkShell {
  nativeBuildInputs = [
    (python3.withPackages (ps: with ps; [ pyglet mypy ]))
    pandoc
    texliveSmall
  ];
}
