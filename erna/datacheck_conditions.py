conditions = dict()

def create_condition_set(conditionset=['@standard']):
    """
    given a list of conditions create a condition set
    
    If a given condition start with '@NAME', process NAME as a set of conditions defined in the variabel conditions.
    """
    data_conditions = ['fRunTypeName = "data"']
    for condition in conditionset:
        if condition.startswith('@'):
            data_conditions = data_conditions+conditionset[condition[1:]]
        else:
            data_conditions.append(condition)
    return data_conditions
    
conditions['standard'] = [
    'fZenithDistanceMean < 30',
    'fTriggerRateMedian > 40',
    'fTriggerRateMedian < 85',
    'fEffectiveOn > 0.95',
]

conditions['darknight'] = [
    'fCurrentsMedMean < 20',
    'fMoonZenithDistance > 100',
] + conditions['standard']


conditions['low_zenith'] = [
    'fZenithDistanceMax < 30',
]

conditions['no_moonlight'] = [
    'fCurrentsMedMeanBeg < 8',
    'fMoonZenithDistance > 100',
    'fThresholdMinSet < 350',
    'fEffectiveOn > 0.95',
    'fTriggerRateMedian > 40',
    'fTriggerRateMedian < 85',
    'fThresholdMinSet < (14 * fCurrentsMedMeanBeg + 265)'
]

conditions['low_moonlight'] = [
    'fTriggerRateMedian < 85',
    'fZenithDistanceMax < 30',
    'fThresholdMinSet < (14 * fCurrentsMedMeanBeg + 265)',
    'fCurrentsMedMeanBeg > 8',
    'fCurrentsMedMeanBeg <= 16',
]


conditions['moderate_moonlight'] = [
    'fTriggerRateMedian < 85',
    'fThresholdMinSet < (14 * fCurrentsMedMeanBeg + 265)',
    'fCurrentsMedMeanBeg > 32',
    'fCurrentsMedMeanBeg <= 48',
]

conditions['strong_moonlight'] = [
    'fTriggerRateMedian < 85',
    'fThresholdMinSet < (14 * fCurrentsMedMeanBeg + 265)',
    'fCurrentsMedMeanBeg > 64',
    'fCurrentsMedMeanBeg <= 96',
]
