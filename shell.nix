{ mkShell, pandoc, texliveSmall, python3, blender }:

mkShell {
  nativeBuildInputs = [
    (python3.withPackages (ps: with ps; [ pyglet mypy flake8 ]))
    pandoc
    texliveSmall
    blender
  ];
}
