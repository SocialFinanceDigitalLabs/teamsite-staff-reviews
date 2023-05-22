# Social Finance Staff Review Process

This Django App is to support the SF staff review process. 


## External Reviewers

Staff that primarily work with external organisations can nominate external reviewers
by giving name and email address. 

When the review process opens, the staff members all get access to a review
dashboard where they can control their part of the review process. That involves 
submitting their self-assessment, completing any internal reviews, as well as sending
out invitations to the external reviewers. 

There will be a template email section on the review dashboard for external reviewers. 

The initial email contains a six-digit code that's unique for this nomination, i.e. if the
same external has been nominated multiple times, they will get different six-digit codes.

This means the process is always the same, whether a user has one or several invitations
under one or several email addresses. 

Once the reviewer activates their six digit code, they will be asked to enter an email 
address. At this stage an 'account' will be created for them, and the nomination tied
to that account. The email does not have to be the same that the invitation was sent to.
Once the account is created, an email is sent with a 'magic link' (short-lived, 
one-time password) that signs-the user in, and they can complete their reviews.

A cookie is set that allows the user to continue the reviews without requesting another link,
but should they get logged out or wish to use another computer, then a new link can
be sent by entering their email address. 


## Process

### Setup

First it is necessary to create a new Review Period, e.g. **2022 Full Year**. Each period must 
also have a set of stages, and these can easily be created from the Review Period list view
by selecting "Add default stages" from the actions drop-down.

The stages will all have random dates, so it's still necessary to edit these. 

Once the stages have been added, you can add the default form questions. Minor text edits can be made after
setup, but for more significant changes it is necessary to edit the 
[current-questions](../fixtures/current-questions.yml) file.

In summary - to create a new review period:

* Create the period
* Add the stages
* Add the forms

### Stage 4 - Deadline for feedback submissions

### Stage 5 - Part 1 Appraisal Form to be submitted

When this stage opens, two key tasks must be run:

* All line managers must receive a nomination to complete assessment pt1

```shell
./manage.py nominate-assessment-p1 --create
```

As these nominations follow a different schedule for the main one, they have
all closes_override set to the end date of the stage. 

If the end date of the stage changes, it's necessary to run the command again to 
update all the nominations. This will also re-create any that have been removed.

* All line managers should be invited to the sharepoint folders holding the assessment docs for their reports

```shell
./manage.py invite-line-managers
```


