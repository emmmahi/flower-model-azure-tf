## Flower Prediction Website
## Online Learning

Tavoitteena on luoda kukkadatalle tunnistusta tekevä nettisivu Azuren pilvipalveluun.

![alt text](./images/azure_arkkitehtuuri.png)

Azure CLI ja terraform tarvitaan

````
az login

az account show
````

## Käyttö dockerissa 

**docker-compose.yml** -> pitää ajaa ylös ennen scripiten ajoa, koska luo kontit niitä varten!


````
docker compose up -d
docker ps
docker compose logs -f
````

## Azure Blob Storage
*Azure Blob Storage on Microsoft Azure -pilvipalvelun tarjoama skaalautuva, kustannustehokas ja turvallinen palvelu, joka on suunniteltu erityisesti suurten tietomäärien tallentamiseen ja hallintaan. "Blob" on lyhenne sanoista Binary Large Object, ja se viittaa suuriin tiedostoihin tai binääritietoihin, kuten asiakirjoihin, kuviin, videoihin tai varmuuskopioihin.* 





## Terraform & Azure

* Container Registryn pystytys: 

````
cd infta/tf/container_registry
terraform init
terraform apply
````
![alt text](./images/azure_view.png)


* Imaget konttirekisteriin:
````
cd scripts/
./01_acr_login.sh # kirjaudu konttirekisteriin
./02_build_n_release flowerui 1.0  #vie image ja versio
./02_build_n_release flowerpredict 1.0
./02_build_n_release modeller 1.0
````

* Palveluiden pystytys Azureen

````
cd infra/tf/services
terraform init
terraform apply
````




### MITÄ TEIN

1. virtuaaliympäristön luominen. testailin paikallisesti emulaattorin avulla testausta, että saan mallin ja datasetin oikeaan paikkaan ja jonoon lisäyksen toimimaan (docker compose azurite ja populate, src/azurire**)
2. drawhello lisäys src:een, docker composeen lisäys ja ui:n käyttö onnistui paikallisesti
3. terraform alustus, infra/tf/container registry konttirekisterä varten, minne voi scripteillä viedä imageja src:n alta
4. palvelun luonti, oma terraform apply siellä. main ja variables osioihin niiden konttien lisäys, mitkä on scriptillä viety konttirekisteriin. 

**tf/container_registry**
* luo Azure recource groupin ja azure conatiner registryn
    * rg-emma-olearn-acr
    * cremmaolearn
        * = "cr${var.identifier}${var.course_short_name}"

**tf/services**
* luo azure recourge group
    * rg-emma-olearn
* luo storage account
    * saemmaolearn
* luo storage container
    * st-emma-olearn
* luo storage queue
    * sq-emma-olearn
* luo storage containeriin blobit tiedostoja varten (data ja mallit)
    * st-emma-olearn -> "kansiot" models ja datasets
* luo azure container group
    * ci-emma-olearn
