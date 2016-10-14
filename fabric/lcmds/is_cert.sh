#!/bin/bash - 
#===============================================================================
#
#          FILE: is_cert.sh
# 
#         USAGE: ./is_cert.sh 
# 
#   DESCRIPTION: 
# 
#       OPTIONS: ---
#  REQUIREMENTS: ---
#          BUGS: ---
#         NOTES: ---
#        AUTHOR: Marek Płonka (marekpl), marek.plonka@nask.pl
#  ORGANIZATION: NASK
#       CREATED: 07.10.2016 10:05:26
#      REVISION:  ---
#===============================================================================

set -o nounset                              # Treat unset variables as an error

is_cert=false
[[ -f /etc/pki/tls/certs/wild.dro.nask.pl.crt ]] && c1=true || c1=false
[[ -f /etc/pki/tls/certs/chain.dro.nask.pl.crt ]] &&  c2=true || c2=false
[[ -f /etc/pki/tls/private/wild.dro.nask.pl.key ]] &&  c3=true || c3=false

#[[ $c1 -a $c2 -a $c3 ]] && echo "ok" || echo "ERR"

if  $c1 -a $c2 -a $c3; then
    echo "ok"
else
    echo "ERR"
fi
