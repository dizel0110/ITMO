import json

import pandas as pd

mkb10_leveled = pd.read_csv('akcent_graph/utils/neo/data/mkb_10_level.csv')

mkb10_leveled_01 = mkb10_leveled[mkb10_leveled['LEVEL'] == 1]
mkb10_leveled_02 = mkb10_leveled[mkb10_leveled['LEVEL'] == 2]
mkb10_leveled_03 = mkb10_leveled[mkb10_leveled['LEVEL'] == 3]
mkb10_leveled_04 = mkb10_leveled[mkb10_leveled['LEVEL'] == 4]
mkb10_leveled_05 = mkb10_leveled[mkb10_leveled['LEVEL'] == 5]
mkb10_leveled_06 = mkb10_leveled[mkb10_leveled['LEVEL'] == 6]

with open('akcent_graph/utils/neo/data/fixtures/NeoBodySystem.json', 'r') as json_file:
    bodysystem_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoOrgan.json', 'r') as json_file:
    organ_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/BodySystemOrganRel.json', 'r') as json_file:
    bodysystemorganrel_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoOrganStructure.json', 'r') as json_file:
    organstructure_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoAnatomicalFeature.json', 'r') as json_file:
    anatomicalfeature_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoAnatomicalValue.json', 'r') as json_file:
    anatomicalvalue_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/AnatomicalFeatureAnatomicalValueRel.json', 'r') as json_file:
    anatomicalfeatureanatomicalvalue_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoAnomality.json', 'r') as json_file:
    anomality_features = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoBodyFluids.json', 'r') as json_file:
    bodyfluids_features = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoSymptomFeature.json', 'r') as json_file:
    symptomfeature_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoSymptomValue.json', 'r') as json_file:
    symptomvalue_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/SymptomFeatureSymptomValueRel.json', 'r') as json_file:
    symptomfeaturessymptomvaluerel_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoTherapyFeature.json', 'r') as json_file:
    therapyfeature_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoTherapyValue.json', 'r') as json_file:
    therapyvalue_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/TherapyFeatureTherapyValueRel.json', 'r') as json_file:
    therapyfeaturessymptomvaluerel_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoInspectionFeature.json', 'r') as json_file:
    inspectionfeature_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoInspectionValue.json', 'r') as json_file:
    inspectionvalue_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/InspectionFeatureInspectionValueRel.json', 'r') as json_file:
    inspectionfeaturesinspectionvaluerel_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoMedServiceFeature.json', 'r') as json_file:
    med_service_feature_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/NeoMedServiceValue.json', 'r') as json_file:
    med_service_value_fixtures = json.load(json_file)

with open('akcent_graph/utils/neo/data/fixtures/MedServiceFeaturesValuesRelation.json', 'r') as json_file:
    med_service_features_values_fixtures = json.load(json_file)
