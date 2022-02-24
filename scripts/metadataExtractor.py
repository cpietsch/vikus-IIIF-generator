import logging

class MetadataExtractor:
    def __init__(self, *args, **kwargs):
        self.logger = kwargs.get('logger', logging.getLogger('rich'))
        
    def extract(self, manifests):
