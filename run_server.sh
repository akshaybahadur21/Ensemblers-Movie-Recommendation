#! /bin/bash

arg1=$1

if [[ $arg1 == "dev" ]]
then
  cd backend/src/gen && FLASK_ENV=development python -m ensemblers_web
elif [[ $arg1 == "prod" ]]
then
  cd backend/src/gen && FLASK_ENV=production python -m ensemblers_web
else
  echo "Unknown arugment 1 :"$arg1
fi
