pipeline {
  environment {
    registry = "shiznit/redswitch"
    registryCredential = 'tMU0etJEH7R8'
    dockerImage = ''
  }
stages {
  agent any
     stage('Building image') {
      steps{
        script {
          dockerImage = docker.build registry + ":$BUILD_NUMBER"
        }
      }
    }
    stage('Deploy Image') {
      steps{
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
