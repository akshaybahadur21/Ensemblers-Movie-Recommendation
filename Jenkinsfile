pipeline {
    environment {
        DATABASE_URI_PROD = credentials('DATABASE_URI_PROD')
        API_KEY_PROD = credentials('API_KEY_PROD')
    }

    agent {
        dockerfile { 
            filename 'Dockerfile.test'
            args '--user 0:0'
        }
    }
    // options {
    //     // This is required if you want to clean before build
    //     skipDefaultCheckout(true)
    // }

    stages {
        stage('Checkout Code') {
            steps {
                // Clean before build
                // cleanWs()
                echo 'Starting code checkout stage.'
                git branch: env.BRANCH_NAME, credentialsId: 'oscar-token', url: 'https://github.com/cmu-seai/group-project-s22-ensemblers.git'
                echo 'Code checked out successfully.'
            }
        }

        stage('Install Dependencies') {
           steps {
               echo 'Setting up Kafka tunnel'
               sh '''
                    #!/bin/bash
                    sshpass -p "seaitunnel" ssh -o StrictHostKeyChecking=no -L 9092:localhost:9092 tunnel@128.2.204.215 -NTf
               '''
               echo 'Installing dependencies'
                sh '''
                    #!/bin/bash
                    pip install -r requirements.txt
                '''
           }
        }

        stage('Generate Code for Web Server') {
            steps {
                sh '''
                    #!/bin/bash
                    touch backend/src/impl/.env
                    echo "DATABASE_URI_PROD=\"${DATABASE_URI_PROD}\"" >> backend/src/impl/.env
                    echo "API_KEY_PROD=\"${API_KEY_PROD}\"" >> backend/src/impl/.env
                    chmod a+x ./openapi/gen_api_layer.sh && \
                    ./openapi/gen_api_layer.sh
                '''
           }
        }

        stage('Install Web Server Dependencies') {
           steps {
                sh '''
                    #!/bin/bash
                    pip install -r backend/src/gen/requirements.txt
                '''
           }
        }

        stage('Test Connection to DB') {
           steps {
                sh '''
                    #!/bin/bash
                    python jenkins/test_mongo.py
                '''
           }
        }

        stage('Evaluate Code Quality') {
           steps {
            	echo 'Run tests'
                sh '''
                    #!/bin/bash
                    python -m pytest --cov=./ --cov-report=xml tests/
                '''
                cobertura coberturaReportFile: 'coverage.xml'
                echo 'Code quality check completed.'
            }
        }

        stage('Train and Do Offline Evaluation, Update Model if specified') {
           steps {
                sh '''
                    #!/bin/bash
                    python MovieRecommendation.py application.properties
                '''
            }
        }

    } // stages

    // post {
    //     always {
    //         // Clean after build
    //         cleanWs()
    //     }
    // }
}
