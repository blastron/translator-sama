#!/bin/bash

rm test/out/*

for input in test/in/*.txt
do
  echo "==========================================="
  reference=${input/in/out_ref}
  output=${input/in/out}
  echo "python3 translator.py $input $output"
  python3 translator.py $input $output > /dev/null
  echo "diff $reference $output"
  diff $reference $output
  echo "==========================================="
  echo
done
