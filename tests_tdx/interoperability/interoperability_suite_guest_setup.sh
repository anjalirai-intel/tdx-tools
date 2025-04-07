#!/bin/bash
set -x

# test data set
mkdir -p ./download
if [[ ! -f ./download/dien_bf16_pretrained_opt_model.pb ]]; then
    wget -P ./download https://storage.googleapis.com/intel-optimized-tensorflow/models/v2_5_0/dien_bf16_pretrained_opt_model.pb 
fi

if [[ ! -f ./download/dien_fp32_static_rnn_graph.pb ]]; then
    wget -P ./download https://storage.googleapis.com/intel-optimized-tensorflow/models/v2_5_0/dien_fp32_static_rnn_graph.pb 
fi

if [[ ! -f ./download/mobilenet_v1_1.0_224_frozen.pb ]]; then
    wget -P ./download https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_8/mobilenet_v1_1.0_224_frozen.pb
fi

if [[ ! -f ./download/mobilenetv1_int8_pretrained_model.pb ]]; then
    wget -P ./download https://storage.googleapis.com/intel-optimized-tensorflow/models/v1_8/mobilenetv1_int8_pretrained_model.pb
fi

mkdir -p ./download/dien
if [[ ! -f ./download/data.tar.gz ]]; then
    wget -P ./download https://zenodo.org/record/3463683/files/data.tar.gz
    tar -C ./download/ -jxvf ./download/data.tar.gz
    mv ./download/data/* ./download/dien
fi

if [[ ! -f ./download/data1.tar.gz ]]; then
    wget -P ./download https://zenodo.org/record/3463683/files/data1.tar.gz
    tar -C ./download/ -jxvf ./download/data1.tar.gz
    mv ./download/data1/* ./download/dien
fi

if [[ ! -f ./download/data2.tar.gz ]]; then
    wget -P ./download https://zenodo.org/record/3463683/files/data2.tar.gz
    tar -C ./download/ -jxvf ./download/data2.tar.gz
    mv ./download/data2/* ./download/dien
fi

if [[ ! -d ./download/models-2.5.0 ]]; then
    git clone https://github.com/IntelAI/models.git -b v2.5.0 ./download/models-2.5.0
fi

cp -rf ./download/* /root/