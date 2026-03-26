def is_infodesk(user) -> bool:
    """Return True if the user is a member of the InfoDesk group."""
    return user.groups.filter(name='InfoDesk').exists()


def is_race_management(user) -> bool:
    """Return True if the user is a member of the RaceManagement group."""
    return user.groups.filter(name='RaceManagement').exists()
