#!/bin/bash

# By default, use the same directory as this script as output directory
MYSQL_DIR="/tmp/mysqldir"
MYSQL_CO_DIR="/var/lib/mysql-files/"
CONTAINER_NAME=workload-test
LOOP=80

usage() {
    cat << EOM
Usage: $(basename "$0") [OPTION]...
  -r <number>  insert number
  -h Show this
EOM
    exit 0
}

process_args() {
    while getopts ":r:h" option; do
        case "${option}" in
            r) LOOP=${OPTARG};;
            h) usage;;
        esac
    done

}

run_test() {
    now=$(date +"%Y_%m_%d-%H_%M_%S")

    # create mysql test container
    mkdir -p ${MYSQL_DIR}
    echo "create mysql contianer"
    docker run --name ${CONTAINER_NAME} -v ${MYSQL_DIR}:${MYSQL_CO_DIR} -d lei97/mysql:devel
    sleep 30 # wait mysql to start

    # create table
    echo "create database"
    docker exec ${CONTAINER_NAME} mysql -Bse "CREATE DATABASE testDB;"
    echo "create table"
    docker exec ${CONTAINER_NAME} mysql -Bse "CREATE TABLE testDB.testTB(id int NOT NULL, uuid int, PRIMARY KEY(id));"
    
    # Continuously insert data into the table
    for i in `seq $LOOP`
    do
        echo $i TS: $(date +"%T")
        docker exec ${CONTAINER_NAME} mysql -Bse "INSERT INTO testDB.testTB VALUES (${i},${i});"
        sleep 1
    done

    echo "finish insert"
    docker exec ${CONTAINER_NAME} mysql -Bse "SELECT count(*) FROM testDB.testTB INTO OUTFILE '/var/lib/mysql-files/result.txt';"
}

run_web_server() {
    docker run -it --rm -d -p 8080:80 --name web nginx
}

 clean_up() {
    docker rm -f ${CONTAINER_NAME}
    rm -rf ${MYSQL_DIR}
 }

process_args $@
clean_up
run_web_server
run_test