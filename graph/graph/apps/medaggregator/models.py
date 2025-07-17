from typing import Any, Optional

from django.db import models
from django.db.models import Q, UniqueConstraint
from django.utils.translation import gettext_lazy as _
from neomodel import (  # ZeroOrOne,
    ArrayProperty,
    FloatProperty,
    IntegerProperty,
    JSONProperty,
    OneOrMore,
    RelationshipTo,
    StringProperty,
    StructuredNode,
    StructuredRel,
)

from akcent_graph.apps.medaggregator.enums import DiagnosisType
from akcent_graph.apps.medaggregator.helpers import (
    DataCreatedByNeuro,
    DataImportanceFeature,
    DataParentNotFound,
    DataProtocolAttention,
)


class PatientMedcard(models.Model):
    medcard_id = models.CharField(_('Medcard ID'), max_length=50, blank=True)
    user_id = models.CharField(_('User ID'), max_length=50, blank=True)
    created_at = models.DateField(auto_now_add=True, editable=False)
    reprocessed_at = models.DateTimeField(_('Reprocessed at'), null=True, blank=True)
    additional_marked_with_errors = models.BooleanField(_('Additional marked with errors'), default=False)
    logging_from_marked = models.TextField(_('Logging from marked'), blank=True)

    class Meta:
        verbose_name = _('Medcard information')
        verbose_name_plural = _('Medcards information')
        unique_together = (('user_id', 'medcard_id'),)
        ordering = ('-created_at',)

    def __str__(self) -> str:
        return f'{self.pk}: {self.medcard_id}'


class Protocol(models.Model):
    patient_medcard = models.ForeignKey(
        PatientMedcard,
        on_delete=models.CASCADE,
        verbose_name=_('Patient Medcard ID'),
        related_name='protocols',
    )
    protocol_custom_id = models.CharField(
        _('Protocol Custom ID'),
        max_length=50,
        blank=True,
        help_text=_('User-defined arbitrary string. Do not edit manually!'),
    )
    service_id = models.IntegerField(_('Service ID'), null=True, blank=True)
    protocol_data = models.JSONField(_('Protocol data'), null=True, blank=True)
    created_at = models.DateField(auto_now_add=True, editable=False)
    loaded_to_graphdb_at = models.DateTimeField(_('Loaded to Neo at'), null=True, blank=True)
    classified_at = models.DateTimeField(_('Classified at'), null=True, blank=True)
    unmarked_features_left = models.BooleanField(_('Unmarked features left'), default=False)
    attentions_changed = models.BooleanField(_('Attention(s) changed'), default=False)
    marked_with_errors = models.BooleanField(_('Marked with errors'), default=False)
    logging_from_marked = models.TextField(_('Logging from marked'), blank=True)
    is_medtest = models.BooleanField(_('This is medtest'), default=False)

    class Meta:
        verbose_name = _('Protocol')
        verbose_name_plural = _('Protocols')
        constraints = [
            UniqueConstraint(
                fields=['patient_medcard', 'protocol_custom_id', 'is_medtest'],
                condition=~Q(protocol_custom_id=''),
                name='unique_medcard_protocol_custom_id',
            ),
        ]

    def __str__(self) -> str:
        return f'{self.pk}: {self.protocol_custom_id}'


class Speciality(models.Model):
    name = models.CharField(_('Name'), max_length=150, unique=True)

    class Meta:
        verbose_name = _('Speciality')
        verbose_name_plural = _('Specialities')
        indexes = [
            models.Index(fields=['name']),
        ]

    def __str__(self) -> str:
        return f'{self.name}'


class Diagnosis(models.Model):
    patient_medcard = models.ForeignKey(
        PatientMedcard,
        on_delete=models.CASCADE,
        verbose_name=_('Patient Medcard'),
        related_name='diagnoses',
    )
    name = models.CharField(_('Name'), max_length=500)
    description = models.TextField(_('Description'), blank=True)
    date_created = models.DateField(_('Date created'), auto_now_add=True)
    diagnosis_type = models.PositiveSmallIntegerField(
        _('Diagnosis type'),
        choices=DiagnosisType.choices,
        null=True,
        blank=True,
    )
    protocols = models.ManyToManyField(
        Protocol,
        verbose_name=_('Protocols'),
        related_name='diagnoses',
        blank=True,
    )
    is_sent_to_lk = models.BooleanField(_('Is sent to LK'), default=False)
    doctor_specialties = models.ManyToManyField(
        Speciality,
        verbose_name=_('Doctor specialties'),
        related_name='diagnoses',
        blank=True,
    )
    is_general = models.BooleanField(
        _('Visible to all doctors'),
        default=True,
        help_text=_('If set to true, Doctor specialties field is being ignored'),
    )

    class Meta:
        verbose_name = _('Diagnosis')
        verbose_name_plural = _('Diagnoses')
        ordering = ('date_created',)
        indexes = [
            models.Index(fields=['date_created']),
        ]

    def __str__(self) -> str:
        return f'{self.patient_medcard}: {self.name}'


class PatientStringParam(models.Model):
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.CASCADE,
        verbose_name=_('Diagnosis'),
        related_name='string_params',
    )
    group_id = models.CharField(_('Group ID'), max_length=50, blank=True)
    name = models.CharField(_('Name'), max_length=500)
    description = models.TextField(_('Description'), blank=True)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.SET_NULL,
        verbose_name=_('Protocol'),
        related_name='string_params',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Patient string parameter')
        verbose_name_plural = _('Patients string parameters')

    def __str__(self) -> str:
        return f'{self.name}'


class PatientDigitalParam(models.Model):
    diagnosis = models.ForeignKey(
        Diagnosis,
        on_delete=models.CASCADE,
        verbose_name=_('Diagnosis'),
        related_name='digital_params',
    )
    group_id = models.CharField(_('Group ID'), max_length=50)
    name = models.CharField(_('Name'), max_length=500)
    value = models.DecimalField(_('Value'), max_digits=9, decimal_places=2)
    protocol = models.ForeignKey(
        Protocol,
        on_delete=models.SET_NULL,
        verbose_name=_('Protocol'),
        related_name='digital_params',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Patient digital parameter')
        verbose_name_plural = _('Patients digital parameters')

    def __str__(self) -> str:
        return f'{self.name}'


class NeoNodeData(models.Model):
    neo_node_id = models.PositiveIntegerField()
    protocol_json = models.JSONField()
    value = models.TextField()
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = _('Neo Node Data')
        verbose_name_plural = _('Neo Nodes Data')

    def __str__(self) -> str:
        return f'Neo Node Data {self.neo_node_id}'


class NeoNode(models.Model):
    neo_node_data = models.ForeignKey(NeoNodeData, on_delete=models.CASCADE)
    patient_medcard = models.ForeignKey(PatientMedcard, on_delete=models.CASCADE)
    created_at = models.DateField(auto_now_add=True)

    class Meta:
        verbose_name = _('Neo Node')
        verbose_name_plural = _('Neo Nodes')

    def __str__(self) -> str:
        return f'Neo Node {self.pk} for Medcard {self.patient_medcard.medcard_id}'


class NeoAttentioned(StructuredRel):
    """
    patient_id: id of patient\n
    timestamp: time of investigation\n
    protocol_pk: pk of protocol\n
    created_by_neuro: created by neuro flag\n
    parent_not_found: not found parent flag\n
    attention: special importance flag\n
    chain: chain of nodes\n
    value: some artifacts that can be a new class\n
    score: score property
    """

    patient_id = IntegerProperty(default=-1)
    timestamp = StringProperty(default='None')
    protocol_pk = IntegerProperty(default=-1)
    created_by_neuro = IntegerProperty(default=DataCreatedByNeuro.NONE.value)
    parent_not_found = IntegerProperty(default=DataParentNotFound.NONE_PARENT.value)
    attention = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    chain = StringProperty(defailt='')
    value = StringProperty(default='')
    score = FloatProperty(default=None)


class NeoStatused(StructuredRel):
    """
    status: special integer importance flag
    """

    status = IntegerProperty(default=None)


class NeoPatient(StructuredNode):
    """
    name: pk of patient\n
    to_protocol:relationship one or more to protocol node\n
    to_organ:relationship one or more to organ node

    Methods:
    --------
    \n\tget_all_nodes_by_attention\n
    \n\tget_anamnesis

    """

    name = IntegerProperty(Unique_Index=True, required=True)
    to_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )

    def get_all_nodes_by_attention(
        self,
        attention: int = DataImportanceFeature.TRUE_IMPORTANCE.value,
    ) -> Any:
        """
        attention: special importance flag\n
        query_current_nodes: return results_nodes using or not attention\n
        results_nodes: list of node type, node name, relationship\n
        element[0][0]: node type\n
        element[0][1]: node name\n
        element[1]: node name (can be used to order by it for example in cypher query)\n
        element[2]: relationship as python object\n
        result_node: [[type node, name node], [protocol_pk, value, chain]]

        """
        if attention == DataImportanceFeature.ALL_IMPORTANCES.value:
            # Cypher query to obtain type of all nodes, their names and relationships,
            # which are related with patient having patient_id (general case).
            query_current_nodes = """\
            MATCH (u:NeoPatient {name: $name})<-[r:TO_PATIENT]-(other)
            RETURN labels(other), other.name, r
            """
        else:
            # This query find all nodes, their names and relationships
            # filtered by attention.
            query_current_nodes = """\
            MATCH (u:NeoPatient {name: $name})<-[r:TO_PATIENT]-(other)
            WHERE other.attention_required = $attention
            RETURN labels(other), other.name, r
            """
        params_nodes = {'name': self.name, 'attention': attention}
        results_nodes, _ = self.cypher(query_current_nodes, params_nodes)
        result_node = []
        for element in results_nodes:
            to_result_node_2 = []
            type_of_node = element[0][0]
            name_of_node = element[1]
            to_result_node = type_of_node, name_of_node
            to_result_node_2.append(element[2]._properties.get('protocol_pk'))
            if element[2]._properties.get('value'):
                to_result_node_2.append(element[2]._properties.get('value'))
                to_result_node_2.append(element[2]._properties.get('chain'))
            if to_result_node_2:
                full_result = to_result_node, to_result_node_2
                result_node.append(full_result)
        return result_node

    def get_all_protocols_by_attention(
        self,
        attention: list[int],
    ) -> list[int]:
        """
        attention: special importance flag\n
        query: return name_protocols using or not attention\n

        """
        if DataProtocolAttention.ALL.value in attention:
            # This query find all name protocols.
            query = """\
            MATCH (u:NeoPatient {name: $name})<-[r:TO_PATIENT]-(protocol:NeoProtocol)
            RETURN DISTINCT(protocol.name)
            """
        else:
            # This query find all name protocols filtered by attention.
            query = """\
            MATCH (u:NeoPatient {name: $name})<-[r:TO_PATIENT]-(protocol:NeoProtocol)
            WHERE protocol.attention_required IN $attention
            RETURN DISTINCT(protocol.name)
            """
        params_nodes = {'name': self.name, 'attention': attention}
        name_protocols, _ = self.cypher(query, params_nodes)
        protocols = []
        for protocol in name_protocols:
            protocols.append(protocol[0])
        return protocols

    def get_anamnesis(
        self,
        attention: int = DataImportanceFeature.TRUE_IMPORTANCE.value,
    ) -> Any:
        query_paths = """\
        MATCH (patient:NeoPatient {name: $name})-[rp:TO_PROTOCOL]->(protocol:NeoProtocol)
        OPTIONAL MATCH(protocol)<-[st:TO_PROTOCOL]-(other)
        WHERE st.chain <> 'None'
        AND st.attention = $attention
        RETURN st.chain
        """
        query_anamnesis = """\
        MATCH (patient:NeoPatient {name: $name})-[rp:TO_PROTOCOL]->(protocol:NeoProtocol)
        OPTIONAL MATCH(protocol)<-[st:TO_PROTOCOL]-(other)
        WHERE st.chain = $path
        RETURN protocol.name, st.chain, st.value, st.timestamp, st.attention
        ORDER BY st.timestamp
        """
        params = {'name': self.name, 'attention': attention}
        find_paths, _ = self.cypher(query_paths, params)
        paths = []
        for result in find_paths:
            if result[0] not in paths:
                paths.append(result[0])
        anamnesis = {}
        for path in paths:
            params = {'name': self.name, 'path': path}
            results_anamnesis, _ = self.cypher(query_anamnesis, params)
            results_anamnesis_filtered = []
            for element in results_anamnesis:
                if element[1]:
                    results_anamnesis_filtered.append(element)
            anamnesis[path] = results_anamnesis_filtered
        return anamnesis

    def get_anamnesis_according_protocols_with_disease(
        self,
        protocols_pk: Optional[list[str]] = None,
    ) -> Any:
        query_paths = """\
        MATCH (patient:NeoPatient {name: $name})-[rp:TO_PROTOCOL]->(protocol:NeoProtocol)
        WHERE protocol.name IN $protocols_pk
        OPTIONAL MATCH(protocol)<-[st:TO_PROTOCOL]-(other)
        WHERE st.chain <> '' AND st.attention = $attention
        RETURN st.chain
        """
        query_anamnesis = """\
        MATCH (patient:NeoPatient {name: $name})-[rp:TO_PROTOCOL]->(protocol:NeoProtocol)
        WHERE protocol.name IN $protocols_pk
        OPTIONAL MATCH(protocol)<-[st:TO_PROTOCOL]-(other)
        WHERE st.chain = $path
        RETURN protocol.name, st.chain, st.value, st.timestamp
        ORDER BY st.timestamp
        """
        params = {
            'name': self.name,
            'protocols_pk': protocols_pk,
            'attention': DataImportanceFeature.TRUE_IMPORTANCE.value,
        }
        find_paths, _ = self.cypher(query_paths, params)
        paths = []
        for result in find_paths:
            if result[0] not in paths:
                paths.append(result[0])
        anamnesis = {}
        for path in paths:
            params = {'name': self.name, 'path': path, 'protocols_pk': protocols_pk}
            results_anamnesis, _ = self.cypher(query_anamnesis, params)
            results_anamnesis_final = []
            for element in results_anamnesis:
                if element[1]:
                    results_anamnesis_final.append(element)
            if results_anamnesis_final:
                anamnesis[path] = results_anamnesis_final
        return anamnesis

    def get_all_diseases_according_protocols(
        self,
    ) -> Any:
        """
        query_patient_diseases: return all not distinct diseases with relevant protocol_pk\n
        results_diseases: list of disease name, disease treecode and protocol_pk\n
        """
        # This query find all diseases according protocols
        # ordered by disease name and protocol_pk.
        query_patient_diseases = """\
        MATCH (patient:NeoPatient {name: $name})-[rp:TO_PROTOCOL]->(protocol:NeoProtocol)
        OPTIONAL MATCH(protocol)<-[st:TO_PROTOCOL]-(disease:NeoDisease)
        RETURN disease.name, disease.treecode, protocol.name
        ORDER BY disease.name, protocol.name
        """
        params_patient = {'name': self.name}
        results_diseases, _ = self.cypher(query_patient_diseases, params_patient)
        return results_diseases


class NeoProtocol(StructuredNode):
    """
    name: pk of protocol\n
    patient_id: id of patient\n
    timestamp: protocol data\n
    attention_required: required special importance flag\n
    # protocol_info: full information\n
    to_protocolfeature: relationship to protocol feature node\n
    to_organ: relationship to organ node\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_01: relationship to neomkb10_level_01 node\n
    to_neomkb10_level_02: relationship to neomkb10_level_02 node\n
    to_neomkb10_level_03: relationship to neomkb10_level_03 node\n
    to_neomkb10_level_04: relationship to neomkb10_level_04 node\n
    to_neomkb10_level_05: relationship to neomkb10_level_05 node\n
    to_neomkb10_level_06: relationship to neomkb10_level_06 node\n
    to_anatomicalfeature: relationship to anatomicalfeature node\n
    to_symptomfeature: relationship to symptomfeature node\n
    to_inspectionfeature: relationship to inspectionfeature node\n
    to_med_service: relationship to med service node\n
    to_therapyfeature: relationship to therapyfeature node\n
    to_patientanthropometryfeature: relationship to patientanthropometryfeature node\n
    to_patientdemographyfeature: relationship to patientanthropometryfeature node\n
    backto_patient: reverse relationship to patient node
    """

    name = IntegerProperty(
        Unique_Index=True,
        required=True,
    )
    patient_id = IntegerProperty()
    timestamp = IntegerProperty()
    # timestamp = DateTimeProperty()
    attention_required = IntegerProperty(default=DataProtocolAttention.NONE_FIRST.value)
    # protocol_info = JSONProperty(
    #     default={},
    # )
    to_protocolfeature = RelationshipTo(
        'NeoProtocolFeature',
        'TO_PROTOCOLFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_01 = RelationshipTo(
        'NeoMkb10_level_01',
        'TO_NEOMKB10_LEVEL_01',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_02 = RelationshipTo(
        'NeoMkb10_level_02',
        'TO_NEOMKB10_LEVEL_02',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_03 = RelationshipTo(
        'NeoMkb10_level_03',
        'TO_NEOMKB10_LEVEL_03',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_04 = RelationshipTo(
        'NeoMkb10_level_04',
        'TO_NEOMKB10_LEVEL_04',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_05 = RelationshipTo(
        'NeoMkb10_level_05',
        'TO_NEOMKB10_LEVEL_05',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_06 = RelationshipTo(
        'NeoMkb10_level_06',
        'TO_NEOMKB10_LEVEL_06',
        OneOrMore,
        model=NeoStatused,
    )
    to_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_symptomfeature = RelationshipTo(
        'NeoSymptomFeature',
        'TO_SYMPTOMFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_inspectionfeature = RelationshipTo(
        'NeoInspectionFeature',
        'TO_INSPECTIONFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_med_service = RelationshipTo(
        'NeoMedServiceFeature',
        'TO_MED_SERVICE_FEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_therapyfeature = RelationshipTo(
        'NeoTherapyFeature',
        'TO_THERAPYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_patientanthropometryfeature = RelationshipTo(
        'NeoPatientAnthropometryFeature',
        'TO_PATIENTANTHROPOMETRYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_patientdemographyfeature = RelationshipTo(
        'NeoPatientDemographyFeature',
        'TO_PATIENTDEMOGRAPHYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoBodySystem(StructuredNode):
    """
    name: name of the node\n
    attention_required_count: special counter\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_patientanthropometryfeature: relationship to patientanthropometryfeature node\n
    to_organ: relationship to organ node\n
    to_bodystructure: relationship to bodystructuree node\n
    to_symptomfeature: relationship to symptomfeature node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    attention_required_count = IntegerProperty(default=0)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_patientanthropometryfeature = RelationshipTo(
        'NeoPatientAnthropometryFeature',
        'TO_PATIENTANTHROPOMETRYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_bodystructure = RelationshipTo(
        'NeoBodyStructure',
        'TO_BODYSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_symptomfeature = RelationshipTo(
        'NeoSymptomFeature',
        'TO_SYMPTOMFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoOrgan(StructuredNode):
    """
    name: name of the node\n
    attention_required_count: special counter\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_inspectionfeature: relationship to inspectionfeature node\n
    to_inspectionvalue: relationship to inspectionvalue node\n
    to_anatomicalfeature: relationship to anatomicalfeature node\n
    to_anatomicalvalue: relationship to anatomicalvalue node\n
    to_disease: relationship to disease node\n
    to_organstructure: relationship to organstructure node\n
    backto_bodysystem: reverse relationship to bodysystem node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    attention_required_count = IntegerProperty(default=0)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_inspectionfeature = RelationshipTo(
        'NeoInspectionFeature',
        'TO_INSPECTIONFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_inspectionvalue = RelationshipTo(
        'NeoInspectionValue',
        'TO_INSPECTIONVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalvalue = RelationshipTo(
        'NeoAnatomicalValue',
        'TO_ANATOMICALVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_organstructure = RelationshipTo(
        'NeoOrganStructure',
        'TO_ORGANSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_bodysystem = RelationshipTo(
        'NeoBodySystem',
        'TO_BODYSYSTEM',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoOrganStructure(StructuredNode):
    """
    name: name of the node\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_organstructure: relationship to organstructure node\n
    to_anomality: relationship to anomality node\n
    to_featurestructure: relationship to featurestructure node\n
    backto_organ: reverse relationship to organ node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_organstructure = RelationshipTo(
        'NeoOrganStructure',
        'TO_ORGANSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anomality = RelationshipTo(
        'NeoAnomality',
        'TO_ANOMALITY',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_featurestructure = RelationshipTo(
        'NeoFeatureStructure',
        'TO_FEATURESTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoAnomality(StructuredNode):
    """
    name: name of the node\n
    attention_required: required special importance flag\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_featurestructure: relationship to featurestructure node\n
    to_anatomicalfeature: relationship to anatomicalfeature node\n
    backto_organstructure: relationship to organstructure node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_featurestructure = RelationshipTo(
        'NeoFeatureStructure',
        'TO_FEATURESTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_organstructure = RelationshipTo(
        'NeoOrganStructure',
        'TO_ORGANSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoFeatureStructure(StructuredNode):
    """
    name: name of the node\n
    attention_required:required special importance flag\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    integer_value: reserved value\n
    to_organ: relationship to organ node\n
    to_anatomicalfeature: relationship to anatomicalfeature node\n
    to_anatomicalvalue: relationship to anatomicalvalue node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    integer_value = IntegerProperty()
    to_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_anatomicalvalue = RelationshipTo(
        'NeoAnatomicalValue',
        'TO_ANATOMICALVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoAnatomicalFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:required special importance flag\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    integer_value: reserved value\n
    to_anatomicalvalue: relationship to anatomicalvalue node\n
    to_inspectionfeature: relationship to inspectionfeature node\n
    backto_organ: reverse relationship to organ node\n
    backto_organstructure: reverse relationship to organstructure node\n
    backto_anomality: reverse relationship to anomality node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(
        Unique_Index=True,
        required=True,
    )
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    integer_value = IntegerProperty()
    to_anatomicalvalue = RelationshipTo(
        'NeoAnatomicalValue',
        'TO_ANATOMICALVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_inspectionfeature = RelationshipTo(
        'NeoInspectionFeature',
        'TO_INSPECTIONFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_organstructure = RelationshipTo(
        'NeoOrganStructure',
        'TO_ORGANSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_anomality = RelationshipTo(
        'NeoAnomality',
        'TO_ANOMALITY',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoAnatomicalValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_organ: reverse relationship to organ node\n
    backto_bodyfluids: reverse relationship to bodyfluids node\n
    backto_bodystructure: reverse relationship to bodystructure node\n
    backto_anatomicalfeature: reverse relationship to anatomicalfeature node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_bodyfluids = RelationshipTo(
        'NeoBodyFluids',
        'TO_BODYFLUIDS',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_bodystructure = RelationshipTo(
        'NeoBodyStructure',
        'TO_BODYSTRUCTURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoBodyStructure(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_anatomicalvalue: relationship to anatomicalvalue node\n
    backto_bodysystem: reverse relationship to bodysystem node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patient: reverse relationship to patient node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_anatomicalvalue = RelationshipTo(
        'NeoAnatomicalValue',
        'TO_ANATOMICALVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_bodysystem = RelationshipTo(
        'NeoBodySystem',
        'TO_BODYSYSTEM',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoDisease(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    treecode: \n
    level: \n
    to_diseasevalue: relationship to diseasevalue node\n
    to_neomkb10_level_01 relationship to neomkb10_level_01 node\n
    to_neomkb10_level_02 relationship to neomkb10_level_02 node\n
    to_neomkb10_level_03 relationship to neomkb10_level_03 node\n
    to_neomkb10_level_04 relationship to neomkb10_level_04 node\n
    to_neomkb10_level_05 relationship to neomkb10_level_05 node\n
    to_neomkb10_level_06 relationship to neomkb10_level_06 node\n
    to_organ relationship to organ node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_diseasevalue = RelationshipTo(
        'NeoDiseaseValue',
        'TO_VALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_01 = RelationshipTo(
        'NeoMkb10_level_01',
        'TO_NEOMKB10_LEVEL_01',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_02 = RelationshipTo(
        'NeoMkb10_level_02',
        'TO_NEOMKB10_LEVEL_02',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_03 = RelationshipTo(
        'NeoMkb10_level_03',
        'TO_NEOMKB10_LEVEL_03',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_04 = RelationshipTo(
        'NeoMkb10_level_04',
        'TO_NEOMKB10_LEVEL_04',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_05 = RelationshipTo(
        'NeoMkb10_level_05',
        'TO_NEOMKB10_LEVEL_05',
        OneOrMore,
        model=NeoStatused,
    )
    to_neomkb10_level_06 = RelationshipTo(
        'NeoMkb10_level_06',
        'TO_NEOMKB10_LEVEL_06',
        OneOrMore,
        model=NeoStatused,
    )
    to_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoDiseaseValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoSymptomFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_symptomvalue: relationship to symptomvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_symptomvalue = RelationshipTo(
        'NeoSymptomValue',
        'TO_SYMPTOMVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoSymptomValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_symptomfeature = RelationshipTo(
        'NeoSymptomFeature',
        'TO_SYMPTOMFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoInspectionFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_disease: relationship to disease node\n
    to_inspectionvalue: relationship to inspectionvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_organ: reverse relationship to organ node\n
    backto_anatomicalfeature: reverse relationship to anatomicalfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_inspectionvalue = RelationshipTo(
        'NeoInspectionValue',
        'TO_INSPECTIONVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_organ = RelationshipTo(
        'NeoOrgan',
        'TO_ORGAN',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_anatomicalfeature = RelationshipTo(
        'NeoAnatomicalFeature',
        'TO_ANATOMICALFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoInspectionValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_inspectionfeature: reverse relationship to inspectionfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_inspectionfeature = RelationshipTo(
        'NeoInspectionFeature',
        'TO_INSPECTIONFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMedServiceFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_med_service_value: relationship to med_service_value node\n
    to_disease: relationship to disease node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_med_service_value = RelationshipTo(
        'NeoMedServiceValue',
        'TO_MED_SERVICE_VALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMedServiceValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_bodyfluids: reverse relationship to bodyfluids node\n
    backto_med_service_feature: reverse relationship to medservicefeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_bodyfluids = RelationshipTo(
        'NeoBodyFluids',
        'TO_BODYFLUIDS',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_med_service_feature = RelationshipTo(
        'NeoMedServiceFeature',
        'TO_MED_SERVICE_FEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoTherapyFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_therapyvalue: relationship to therapyvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_therapyvalue = RelationshipTo(
        'NeoTherapyValue',
        'TO_THERAPYVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoTherapyValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_therapyfeature: reverse relationship to therapyfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_therapyfeature = RelationshipTo(
        'NeoTherapyFeature',
        'TO_THERAPYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_01(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_02: reverse relationship to neomkb10_level_02 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_02 = RelationshipTo(
        'NeoMkb10_level_02',
        'TO_NEOMKB10_LEVEL_02',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_02(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_03: reverse relationship to neomkb10_level_03 node\n
    backto_neomkb10_level_01: reverse relationship to neomkb10_level_01 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_03 = RelationshipTo(
        'NeoMkb10_level_03',
        'TO_NEOMKB10_LEVEL_03',
        OneOrMore,
        model=NeoStatused,
    )
    backto_neomkb10_level_01 = RelationshipTo(
        'NeoMkb10_level_01',
        'TO_NEOMKB10_LEVEL_01',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_03(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_04: reverse relationship to neomkb10_level_04 node\n
    backto_neomkb10_level_02: reverse relationship to neomkb10_level_02 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_04 = RelationshipTo(
        'NeoMkb10_level_04',
        'TO_NEOMKB10_LEVEL_04',
        OneOrMore,
        model=NeoStatused,
    )
    backto_neomkb10_level_02 = RelationshipTo(
        'NeoMkb10_level_02',
        'TO_NEOMKB10_LEVEL_02',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_04(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_05: reverse relationship to neomkb10_level_05 node\n
    backto_neomkb10_level_03: reverse relationship to neomkb10_level_03 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_05 = RelationshipTo(
        'NeoMkb10_level_05',
        'TO_NEOMKB10_LEVEL_05',
        OneOrMore,
        model=NeoStatused,
    )
    backto_neomkb10_level_03 = RelationshipTo(
        'NeoMkb10_level_03',
        'TO_NEOMKB10_LEVEL_03',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_05(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    to_neomkb10_level_06: reverse relationship to neomkb10_level_06 node\n
    backto_neomkb10_level_04: reverse relationship to neomkb10_level_04 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_neomkb10_level_06 = RelationshipTo(
        'NeoMkb10_level_06',
        'TO_NEOMKB10_LEVEL_06',
        OneOrMore,
        model=NeoStatused,
    )
    backto_neomkb10_level_04 = RelationshipTo(
        'NeoMkb10_level_04',
        'TO_NEOMKB10_LEVEL_04',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoMkb10_level_06(StructuredNode):
    """
    name:\n
    current_id:\n
    parent_id:\n
    treecode:\n
    level:\n
    to_disease: relationship to disease node\n
    backto_neomkb10_level_05: reverse relationship to neomkb10_level_05 node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(Unique_Index=True, required=True)
    current_id = IntegerProperty()
    parent_id = IntegerProperty()
    treecode = StringProperty()
    level = IntegerProperty()
    to_disease = RelationshipTo(
        'NeoDisease',
        'TO_DISEASE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_neomkb10_level_05 = RelationshipTo(
        'NeoMkb10_level_05',
        'TO_NEOMKB10_LEVEL_05',
        OneOrMore,
        model=NeoStatused,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoBodyFluids(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_anatomicalvalue: relationship to anatomicalvalue node\n
    to_med_service_value: relationship to med_service_value node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_anatomicalvalue = RelationshipTo(
        'NeoAnatomicalValue',
        'TO_ANATOMICALVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_med_service_value = RelationshipTo(
        'NeoMedServiceValue',
        'TO_MED_SERVICE_VALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoPatientAnthropometryFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_patientanthropometryvalue: relationship to patientanthtopometryvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_patientanthropometryvalue = RelationshipTo(
        'NeoPatientAnthropometryValue',
        'TO_PATIENTANTHROPOMETRYVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoPatientAnthropometryValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patientanthropometryfeature: reverse relationship to patientanthropometryfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patientanthropometryfeature = RelationshipTo(
        'NeoPatientAnthropometryFeature',
        'TO_PATIENTANTHROPOMETRYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoPatientDemographyFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_patientdemographyvalue: relationship to patientdemographyvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_patientdemographyvalue = RelationshipTo(
        'NeoPatientDemographyValue',
        'TO_PATIENTDEMOGRAPHYVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoPatientDemographyValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_patientdemographyfeature: reverse relationship to patientdemographyfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patientdemographyfeature = RelationshipTo(
        'NeoPatientDemographyFeature',
        'TO_PATIENTDEMOGRAPHYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoProtocolFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_doctorspecialityfeature: relationship to doctorspecialityfeature node\n
    to_therapyfeature: relationship to therapyfeature node\n
    to_protocolvalue: relationship to protocolvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_doctorspecialityfeature = RelationshipTo(
        'NeoDoctorSpecialityFeature',
        'TO_DOCTORSPECIALITYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_therapyfeature = RelationshipTo(
        'NeoTherapyFeature',
        'TO_THERAPYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_protocolvalue = RelationshipTo(
        'NeoProtocolValue',
        'TO_PROTOCOLVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoProtocolValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_inspectionfeature: relationship to inspectionfeature node\n
    to_med_service: relationship to med service node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_inspectionfeature = RelationshipTo(
        'NeoInspectionFeature',
        'TO_INSPECTIONFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    to_med_service = RelationshipTo(
        'NeoMedServiceFeature',
        'TO_MED_SERVICE_FEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoDoctorSpecialityFeature(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    to_doctorspecialityvalue: relationship to doctorspecialityvalue node\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    to_doctorspecialityvalue = RelationshipTo(
        'NeoDoctorSpecialityValue',
        'TO_DOCTORSPECIALITYVALUE',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )


class NeoDoctorSpecialityValue(StructuredNode):
    """
    name: name of the node\n
    attention_required:\n
    patients_ids: list of patient ids visited the node\n
    patients_json: reserved attribute\n
    backto_patient: reverse relationship to patient node\n
    backto_protocol: reverse relationship to protocol node\n
    backto_doctorspecialityfeature: reverse relationship to doctorspecialityfeature node
    """

    name = StringProperty(required=True)
    attention_required = IntegerProperty(default=DataImportanceFeature.NONE_IMPORTANCE.value)
    patients_ids = ArrayProperty()
    patients_json = JSONProperty()
    backto_patient = RelationshipTo(
        'NeoPatient',
        'TO_PATIENT',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_protocol = RelationshipTo(
        'NeoProtocol',
        'TO_PROTOCOL',
        OneOrMore,
        model=NeoAttentioned,
    )
    backto_doctorspecialityfeature = RelationshipTo(
        'NeoDoctorSpecialityFeature',
        'TO_DOCTORSPECIALITYFEATURE',
        OneOrMore,
        model=NeoAttentioned,
    )
