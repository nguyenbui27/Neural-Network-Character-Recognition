#!/bin/zsh
cd "${0:A:h}"
javac Canvas.java Circle.java Recognizer.java Driver.java RunProject.java || exit 1
java RunProject
