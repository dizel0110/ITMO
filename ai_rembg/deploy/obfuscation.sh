#!/bin/bash

output=$(pyarmor --v)

if [[ "$output" == *"License Type    : pyarmor-pro"* ]]; then
     license=true
else
     license=false
fi


if [ "$license" == false ]; then
    if [ -f ./pyarmor-regfile-5393.zip ]; then
       pyarmor register ./pyarmor-regfile-5393.zip
    else
       echo "Can't find registration file"
       exit 1
    fi
fi

pyarmor gen --recursive .

cp -r ./dist/* ./

rm -r ./dist
rm ./pyarmor-regfile-5393.zip

echo "Obfuscation finished"
