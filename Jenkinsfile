pipeline {
  agent none
  environment {
    registry = "shiznit/redswitch"
    registryCredential = 'tMU0etJEH7R8'
    dockerImage = ''
  }
stages {
    stage('git clone') {
        steps {
          git 'https://github.com/nigeldaniels/redswitch.git'
        }
    }

     stage('Building image') {
      steps {
        script {
          dockerImage = docker.build registry + ":$BUILD_NUMBER"
        }
      }
    }
    stage('Deploy Image') {
      steps {
        script {
          docker.withRegistry( '', registryCredential ) {
            dockerImage.push()
          }
        }
      }
    }
    stage('Remove Unused docker image') {
      steps{
        sh "docker rmi $registry:$BUILD_NUMBER"
      }
    }
   }
 }
