# Security Features

This document describes the security features implemented in the PlachtIS system.

## Overview

Three key security features have been implemented to manage user access and registration deadlines:

### 1. User Ownership of Units

**Feature:** Every user can only view and edit the Units (and their associated Participants) that they have created.

**Implementation:**
- Added `created_by` field to the `Unit` model, which links each Unit to the User who created it
- Updated all views to filter Units and Participants by the current user
- In the admin interface, regular users can only see their own Units and Participants
- Staff and superusers can see all Units and Participants in the admin interface

**User Experience:**
- When viewing the unit list, users only see Units they created
- When viewing the participant list, users only see Participants from their own Units
- Attempting to edit another user's Unit will result in a "403 Forbidden" error

### 2. Registration Deadline

**Feature:** Creating new Units and Participants is only allowed until a certain point in time.

**Implementation:**
- Added `EventSettings` model to store event configuration, including the registration deadline
- The `EventSettings` model should have only one instance (enforced in admin)
- All creation views check if registration is still open before allowing new Units/Participants
- Helper methods `EventSettings.is_registration_open()` and `EventSettings.get_registration_deadline()` provide easy access
- All editing views check if editing is still open before allowing edits
- Helper methods `EventSettings.is_editing_open()` and `EventSettings.get_editing_deadline()` provide easy access

**User Experience:**
- Users attempting to create new Units/Participants after the deadline will see an error message
- The error message displays the exact deadline date and time
- Users are redirected to the unit list page

**Admin Configuration:**
- Superusers can set the registration deadline in the Django admin interface
- Navigate to: Admin → Event Settings
- Set the `registration_deadline` field to the desired date and time

### 3. Unlocking Units for Editing

**Feature:** After the registration deadline has passed, privileged users can unlock specific Units to allow further editing.

**Implementation:**
- Added `unlocked_for_editing` boolean field to the `Unit` model
- The `Unit.can_be_edited(user)` method checks:
  1. If the user is the owner of the Unit
  2. If registration is still open OR if the Unit is unlocked for editing
- In the admin interface, only staff/superusers can modify the `unlocked_for_editing` field
- Regular users cannot set this field themselves (it's read-only in forms)

**User Experience:**
- After the deadline, users cannot edit their Units by default
- If a privileged user unlocks a Unit, the owner can edit it again
- Regular users see an error message when trying to edit locked Units

**Admin Operations:**
- To unlock a Unit for editing:
  1. Navigate to: Admin → Units
  2. Find the Unit to unlock
  3. Check the "unlocked for editing" checkbox
  4. Save the Unit
- The owner can now edit this Unit despite the deadline having passed

## Database Migrations

Three migrations were created to implement these features:

1. **0005_add_security_features**: Adds the `EventSettings` model and new fields to `Unit`
2. **0006_assign_units_to_users**: Data migration that assigns existing Units to the first superuser
3. **0007_make_created_by_non_nullable**: Makes the `created_by` field non-nullable

## Setting Up Event Settings

After deploying these changes:

1. Log in to the Django admin interface
2. Navigate to "Event Settings"
3. Click "Add Event Settings" (only if no settings exist)
4. Set:
   - Event name (e.g., "Summer Camp 2026")
   - Registration deadline (date and time when registration closes)
5. Save the settings

## Future Enhancements

To add privileged users who can unlock Units:

1. Create a Django group (e.g., "Event Organizers")
2. Add specific users to this group
3. Update the admin interface to check group membership when showing/hiding the `unlocked_for_editing` field
4. Optionally, create a custom permission for unlocking Units

## Testing Checklist

- [ ] Create a new Unit before the deadline - should succeed
- [ ] Try to create a new Unit after the deadline - should fail with error message
- [ ] Edit your own Unit before the deadline - should succeed
- [ ] Try to edit someone else's Unit - should fail with 403 Forbidden
- [ ] Edit your own Unit after the deadline - should fail with error message
- [ ] As admin, unlock a Unit after the deadline
- [ ] As owner, edit the unlocked Unit after the deadline - should succeed
- [ ] Verify non-admin users cannot see the unlock checkbox
- [ ] Verify unit/participant lists only show user's own data
