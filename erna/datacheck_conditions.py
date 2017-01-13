conditions = dict()

conditions['standard'] = [
    'fRunTypeName = "data"',
    'fZenithDistanceMean < 30',
    'fTriggerRateMedian > 40',
    'fTriggerRateMedian < 85',
    'fEffectiveOn > 0.95',
]

conditions['darknight'] = [
    'fCurrentsMedMean < 20',
    'fMoonZenithDistance > 100',
] + conditions['standard']
