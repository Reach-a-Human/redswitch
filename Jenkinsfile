pipeline {
  agent any
  environment {
    registry = "shiznit/redswitch"
    registryCredential = 'ccc18935-89da-4bdf-abe4-9295f7593427'
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
