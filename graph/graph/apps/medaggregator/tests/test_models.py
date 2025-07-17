def test_models():
    from akcent_graph.apps.medaggregator.models import (
        NeoAnatomicalFeature,
        NeoAnatomicalValue,
        NeoAnomality,
        NeoBodyFluids,
        NeoBodyStructure,
        NeoBodySystem,
        NeoDisease,
        NeoDiseaseValue,
        NeoDoctorSpecialityFeature,
        NeoDoctorSpecialityValue,
        NeoFeatureStructure,
        NeoInspectionFeature,
        NeoInspectionValue,
        NeoMedServiceFeature,
        NeoMedServiceValue,
        NeoMkb10_level_01,
        NeoMkb10_level_02,
        NeoMkb10_level_03,
        NeoMkb10_level_04,
        NeoMkb10_level_05,
        NeoMkb10_level_06,
        NeoOrgan,
        NeoOrganStructure,
        NeoPatient,
        NeoPatientAnthropometryFeature,
        NeoPatientAnthropometryValue,
        NeoPatientDemographyFeature,
        NeoPatientDemographyValue,
        NeoProtocol,
        NeoProtocolFeature,
        NeoProtocolValue,
        NeoSymptomFeature,
        NeoSymptomValue,
        NeoTherapyFeature,
        NeoTherapyValue,
    )

    class_1 = NeoAnatomicalValue()
    class_2 = NeoAnatomicalFeature()
    class_3 = NeoAnomality()
    class_4 = NeoBodyFluids()
    class_5 = NeoBodyStructure()
    class_6 = NeoBodySystem()
    class_7 = NeoDisease()
    class_8 = NeoDiseaseValue()
    class_9 = NeoDoctorSpecialityFeature()
    class_10 = NeoDoctorSpecialityValue()
    class_11 = NeoFeatureStructure()
    class_12 = NeoInspectionFeature()
    class_13 = NeoInspectionValue()
    class_14 = NeoMedServiceFeature()
    class_15 = NeoMedServiceValue()
    class_16 = NeoMkb10_level_01()
    class_17 = NeoMkb10_level_02()
    class_18 = NeoMkb10_level_03()
    class_19 = NeoMkb10_level_04()
    class_20 = NeoMkb10_level_05()
    class_21 = NeoMkb10_level_06()
    class_22 = NeoOrgan()
    class_23 = NeoOrganStructure()
    class_24 = NeoPatient()
    class_25 = NeoPatientAnthropometryFeature()
    class_26 = NeoPatientAnthropometryValue()
    class_27 = NeoPatientDemographyFeature()
    class_28 = NeoPatientDemographyValue()
    class_29 = NeoProtocol()
    class_30 = NeoProtocolFeature()
    class_31 = NeoProtocolValue()
    class_32 = NeoSymptomFeature()
    class_33 = NeoSymptomValue()
    class_34 = NeoTherapyFeature()
    class_35 = NeoTherapyValue()
    relationship_1 = 'backto_patient'
    assert relationship_1 in (dir(class_1) and dir(class_2) and dir(class_3) and dir(class_4) and dir(class_5))
    assert relationship_1 in (dir(class_6) and dir(class_7) and dir(class_8) and dir(class_9) and dir(class_10))
    assert relationship_1 in (dir(class_11) and dir(class_12) and dir(class_13) and dir(class_14) and dir(class_15))
    assert relationship_1 in (dir(class_16) and dir(class_17) and dir(class_18) and dir(class_19) and dir(class_20))
    assert relationship_1 in (dir(class_21) and dir(class_22) and dir(class_23))
    assert relationship_1 not in (dir(class_24))
    assert relationship_1 in (
        dir(class_25) and dir(class_26) and dir(class_27) and dir(class_28) and dir(class_29) and dir(class_30)
    )
    assert relationship_1 in (dir(class_31) and dir(class_32) and dir(class_33) and dir(class_34) and dir(class_35))
