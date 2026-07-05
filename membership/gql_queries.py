import graphene
from graphene_django import DjangoObjectType
from insuree.models import Insuree
from membership.utils.db_helper import SQLiteHelper

# Try to import Claim if claim module exists
try:
    from claim.models import Claim
except ImportError:
    Claim = None

try:
    from insuree.schema import InsureeGQLType
except ImportError:
    class InsureeGQLType(DjangoObjectType):
        class Meta:
            model = Insuree

if Claim:
    try:
        from claim.schema import ClaimGQLType
    except ImportError:
        class ClaimGQLType(DjangoObjectType):
            class Meta:
                model = Claim
else:
    ClaimGQLType = None


class Query(graphene.ObjectType):
    insuree_profile = graphene.Field(InsureeGQLType)
    insuree_claims = graphene.List(ClaimGQLType) if ClaimGQLType else graphene.String()

    def resolve_insuree_profile(self, info):
        user = info.context.user
        if not user.is_authenticated:
            return None
        
        db_helper = SQLiteHelper()
        try:
            insuree_id = db_helper.get_insuree_id_by_user_id(user.i_user_id)
            if insuree_id:
                return Insuree.objects.filter(id=insuree_id).first()
        finally:
            db_helper.close()
        return None

    def resolve_insuree_claims(self, info):
        if not ClaimGQLType:
            return None
        user = info.context.user
        if not user.is_authenticated:
            return []
        
        db_helper = SQLiteHelper()
        try:
            insuree_id = db_helper.get_insuree_id_by_user_id(user.i_user_id)
            if insuree_id:
                insuree = Insuree.objects.filter(id=insuree_id).first()
                if insuree:
                    return Claim.objects.filter(insuree=insuree)
        finally:
            db_helper.close()
        return []
