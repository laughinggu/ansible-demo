#!/bin/bash
 
#Required
domain=$1
commonname=$domain
 
#Change to your company details
country=CN
state=Shanghai
locality=Shanghai
organization=emc.com
organizationalunit=IT
email=xiongz@emc.com
 
#Optional
password=dummypassword
 
if [ -z "$domain" ]
then
    echo "Argument not present."
    echo "Useage $0 [common name]"
 
    exit 99
fi
 
echo "Generating key request for $domain"
 
#Generate a key
openssl genrsa -des3 -passout pass:$password -out $domain.key 2048 -noout
 
#Remove passphrase from the key. Comment the line out to keep the passphrase
echo "Removing passphrase from key"
openssl rsa -in $domain.key -passin pass:$password -out $domain.key
 
#Create the request
echo "Creating CSR"
openssl req -new -key $domain.key -out $domain.csr -passin pass:$password \
    -subj "/C=$country/ST=$state/L=$locality/O=$organization/OU=$organizationalunit/CN=$commonname/emailAddress=$email"
 

#Generate the cert
openssl x509 -req -days 3650 -in $domain.csr -signkey $domain.key -out $domain.crt