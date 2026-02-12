from .base import Command
from .npc_commands import CreateNPCCommand, EditNPCCommand, DeleteNPCCommand, ListNPCsCommand
from .group_commands import CreateGroupCommand, DeleteGroupCommand, ListGroupsCommand
from .claim_commands import CreateClaimCommand, EditClaimCommand, DeleteClaimCommand, ListClaimsCommand
from .constant_commands import CreateObjectCommand, CreatePlaceCommand, ListConstantsCommand
from .opinion_commands import CreateOpinionCommand, DeleteOpinionCommand, ListOpinionsCommand
from .relation_commands import (
    CreateStructuralRelationCommand,
    CreateReferenceCommand,
    CreateMembershipCommand,
    DeleteMembershipCommand,
)
from .mystery_commands import (
    CreateMysteryCommand, DeleteMysteryCommand, ListMysteriesCommand,
    LinkClaimToMysteryCommand, UnlinkClaimFromMysteryCommand,
    ListClaimsByMysteryCommand,
)

__all__ = [
    "Command",
    "CreateNPCCommand", "EditNPCCommand", "DeleteNPCCommand", "ListNPCsCommand",
    "CreateGroupCommand", "DeleteGroupCommand", "ListGroupsCommand",
    "CreateClaimCommand", "EditClaimCommand", "DeleteClaimCommand", "ListClaimsCommand",
    "CreateObjectCommand", "CreatePlaceCommand", "ListConstantsCommand",
    "CreateOpinionCommand", "DeleteOpinionCommand", "ListOpinionsCommand",
    "CreateStructuralRelationCommand",
    "CreateReferenceCommand", "CreateMembershipCommand", "DeleteMembershipCommand",
    "CreateMysteryCommand", "DeleteMysteryCommand", "ListMysteriesCommand",
    "LinkClaimToMysteryCommand", "UnlinkClaimFromMysteryCommand",
    "ListClaimsByMysteryCommand",
]
