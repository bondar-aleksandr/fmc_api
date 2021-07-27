class ApiClassTemplate:
    VALID_JSON_DATA = []
    URL_SUFFIX = ""

    def __init__(self, **kwargs):
        self.parse_kwargs(**kwargs)

    def parse_kwargs(self, **kwargs):
        for key in self.VALID_JSON_DATA:
            if key in kwargs:
                setattr(self, key, kwargs[key])

    def format_data(self):
        json_data = {}
        for key in self.VALID_JSON_DATA:
            if hasattr(self, key):
                json_data[key] = getattr(self, key)
        return json_data



class NetworkObjectFQDN(ApiClassTemplate):
    VALID_JSON_DATA = [
        "id",
        "name",
        "type",
        "value",
        "description",
        "dnsResolution",
        "overridable",
    ]
    URL_SUFFIX = "/object/fqdns"
    VALID_FOR_DNS_RESOLUTION = ["IPV4_ONLY", "IPV6_ONLY", "IPV4_AND_IPV6"]

    def __init__(self, **kwargs):
        self.parse_kwargs(**kwargs)
        self.type = 'fqdn'

    def parse_kwargs(self, **kwargs):
        super().parse_kwargs(**kwargs)
        if "dnsResolution" in kwargs:
            if kwargs["dnsResolution"] in self.VALID_FOR_DNS_RESOLUTION:
                self.dnsResolution = kwargs["dnsResolution"]
        else:
            self.dnsResolution = "IPV4_ONLY"

    def __repr__(self):
        return f'NetworkObject(name={self.name}, type={self.type}, value={self.value})'

# netfqdn = NetworkObjectFQDN(name='asd', value='cisco.com')
# print(netfqdn)