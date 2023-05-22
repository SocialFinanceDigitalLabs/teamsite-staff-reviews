from django.core.exceptions import ObjectDoesNotExist
from graphql_relay import from_global_id


def get_id_from_type(id, expected_type):
    type, pk = from_global_id(id)
    if type != expected_type:
        raise ObjectDoesNotExist("That object does not exist")
    return pk
