# Generates API layer code for backend based on openapi.yaml
# reference: https://stackoverflow.com/a/47554626

script_dir=`dirname "$(realpath $0)"`
project_root=`dirname $script_dir`

OPENAPI_PATH="openapi"
BACKEND_GEN_PATH="backend/src/gen"

# download codegen cli if not exists
cd $script_dir
if [ ! -f swagger-codegen-cli-3.0.29.jar ]; then
    wget https://repo1.maven.org/maven2/io/swagger/codegen/v3/swagger-codegen-cli/3.0.29/swagger-codegen-cli-3.0.29.jar -O swagger-codegen-cli-3.0.29.jar
fi


# backend
# remove src/gen if exists and generate code
# we also create a link to src/impl in src/gen which contains our own implementation
cd $project_root && rm -rf $BACKEND_GEN_PATH && \
mkdir -p $BACKEND_GEN_PATH/ensemblers_web && \
cd $BACKEND_GEN_PATH/ensemblers_web/ && \
ln -sf ../../impl/ && \
cd ../../../.. && \
java -jar $OPENAPI_PATH/swagger-codegen-cli-3.0.29.jar generate \
    -i $OPENAPI_PATH/openapi.yaml \
    -l python-flask \
    -o $BACKEND_GEN_PATH \
    -t backend/templates \
    -c $OPENAPI_PATH/swagger-codegen-config.json

# Couldn't find a way to omit these default files from the templates so manully remove them
cd $BACKEND_GEN_PATH && \
rm Dockerfile .gitignore .travis.yml git_push.sh tox.ini test-requirements.txt .dockerignore setup.py