#!/bin/bash

# Run TPM commands to encrypt and decrypt some data
DATA="hello world"

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -d <data>  data to be encrypted
  -h Show this
EOM
    exit 0
}

process_args() {
    while getopts ":d:h" option; do
        case "${option}" in
            d) DATA=${OPTARG};;
            h) usage;;
        esac
    done

}

clean_env() {
    sudo rm -rf /opt/result
}

run_tpm_test() {
    echo "create RSA key pair"
    tpm2_createprimary -c primary.ctx
    tpm2_create -C primary.ctx -Gaes128 -u key.pub -r key.priv
    tpm2_load -C primary.ctx -u key.pub -r key.priv -c key.ctx

    ret=$?
    if [ $ret -eq 0 ];
    then
        echo "Success to load RSA key"
    else
        echo "Fail to load RSA key, ret: $ret"
        exit $ret
    fi

    echo "Encrypt and Decrypt some data"
    echo ${DATA} > 'secret.dat'
    tpm2_encryptdecrypt -c key.ctx -o secret.enc secret.dat
    tpm2_encryptdecrypt -d -c key.ctx -o secret.dec secret.enc

    ret=$?
    if [ $ret -eq 0 ];
    then
        echo "Success to decrypt ${DATA}"
    else
        echo "Fail to decrypt ${DATA}, ret: $ret"
        exit $ret
    fi
    
    cat secret.dec > /opt/result

}

process_args $@
clean_env
run_tpm_test
