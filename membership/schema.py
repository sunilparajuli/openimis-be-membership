
import graphene

from .gql_queries import Query as MembershipQuery
from .gql_mutations import GeneratePdfSlip, LoginInsuree, RegisterInsuree, VerifyOtp

class Query(MembershipQuery, graphene.ObjectType):
    pass


class Mutation(graphene.ObjectType):
    generate_pdf_slip = GeneratePdfSlip.Field()
    login_insuree = LoginInsuree.Field()
    register_insuree = RegisterInsuree.Field()
    verify_otp = VerifyOtp.Field()
