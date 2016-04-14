#!/bin/bash

rm test/out_md/*

for input in test/in/*.txt
do
  echo "==========================================="
  reference=${input/in/out_ref_md}
  reference_md=${reference/txt/md}
  output=${input/in/out_md}
  output_md=${output/txt/md}
  echo "python3 translator.py $input $output_md"
  python3 translator.py --md $input $output_md > /dev/null
  echo "diff $reference_md $output_md"
  diff $reference_md $output_md
  echo "to update, run:"
  echo "cp $output_md $reference_md"
  echo "==========================================="
  echo
done
