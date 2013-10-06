"""

 gig class for Gig-o-Matic 2 

 Aaron Oppenheimer
 24 August 2013

"""

from google.appengine.ext import ndb
from requestmodel import *
import webapp2_extras.appengine.auth.models

import webapp2

import member
import band
import plan
import assoc
import goemail

from debug import debug_print
import datetime

#
# class for gig
#
class Gig(ndb.Model):
    """ Models a gig-o-matic gig """
    title = ndb.TextProperty()
    contact = ndb.UserProperty()
    details = ndb.TextProperty()
    setlist = ndb.TextProperty()
    date = ndb.DateProperty(auto_now_add=True)
    call = ndb.TimeProperty()
    archive_id = ndb.StringProperty()

#
# Functions to make and find gigs
#

def new_gig(the_band, title, date=None, contact=None, details="", setlist="", call=None):
    """ Make and return a new gig """
    if date is None:
        date = datetime.datetime.now()
    the_gig = Gig(parent=the_band.key, title=title, contact=contact, \
                    details=details, setlist=setlist, date=date, call=call)
    the_gig.put()
    debug_print('new_gig: added new gig: {0} on {1}'.format(title, str(date)))
    return the_gig
                
def get_gig_from_key(key):
    """ Return gig objects by key"""
    return key.get()
        
def get_gigs_for_band(the_band, num=None, start_date=None):
    """ Return gig objects by band"""
        
    if (type(the_band) is not list):
        band_list = [the_band]
    else:
        band_list = the_band

    if start_date:
        # correct the start date in case we're a non-UTC band (everyone, probably)
        # assumes that all the bands are in the same timezone
        test_band=band_list[0]
        print 'raw start date is {0}'.format(start_date)
        if test_band.time_zone_correction:
            # this band is in a non-UTC time zone!
            start_date=start_date+datetime.timedelta(hours=test_band.time_zone_correction)
            print 'tz start date is {0}'.format(start_date)
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        print 'final start date is {0}'.format(start_date)
    
    all_gigs = []
    for a_band in band_list:
        if start_date is None:
            gig_query = Gig.query(ancestor=a_band.key).order(Gig.date)
        else:
            gig_query = Gig.query(Gig.date >= start_date, \
                                  ancestor=a_band.key).order(Gig.date)
        the_gigs = gig_query.fetch()
        debug_print('get_gigs_for_band: got {0} gigs for \
                    band key id {1} ({2})'.format(len(the_gigs), \
                                                  a_band.key.id(), \
                                                  a_band.name))
        all_gigs.append(the_gigs)
        
    # now we have several lists of gigs - merge them
    if len(all_gigs) == 0:
        return None
    elif len(all_gigs) == 1:
        if num is None:
            return all_gigs[0]
        else:
            return all_gigs[:num]
    else:
        # merge the gigs
        sorted_gigs = []
        list1 = all_gigs.pop()    
        while all_gigs:
            list2 = all_gigs.pop()    
            while (list1 and list2):
                if (list1[0].date <= list2[0].date): # Compare both heads
                    item = list1.pop(0) # Pop from the head
                    sorted_gigs.append(item)
                else:
                    item = list2.pop(0)
                    sorted_gigs.append(item)

            # Add the remaining of the lists
            sorted_gigs.extend(list1 if list1 else list2)
            # now prepare to loop back
            list1 = sorted_gigs
            sorted_gigs = []

    sorted_gigs = list1
    print 'sorted gigs got {0}'.format(len(list1))

    if num is None:
        return list1
    else:
        return list1[:num]
    
    
    
def get_gigs_for_band_for_dates(the_band, start_date, end_date):
    """ Return gig objects by band"""
    gig_query = Gig.query(ndb.AND(Gig.date >= start_date, \
                                  Gig.date <= end_date), \
                                  ancestor=the_band.key).order(Gig.date)
    gigs = gig_query.fetch()
    debug_print('get_gigs_for_band_for_dates: got {0} gigs for \
                 band key id {1} ({2})'.format(len(gigs), \
                                                the_band.key.id(), \
                                                the_band.name))
    return gigs

def get_gigs_for_member_for_dates(the_member, start_date, end_date):
    """ return gig objects for the bands of a member """
    the_bands = member.get_confirmed_bands_of_member(the_member)
    all_gigs = []
    for a_band in the_bands:
        all_gigs.extend(get_gigs_for_band_for_dates(a_band, \
                                                    start_date, \
                                                    end_date))
    return all_gigs

def make_archive_for_gig_key(the_gig_key):
    """ makes an archive for a gig - files away all the plans, then delete them """

    the_members_by_section = band.get_member_keys_of_band_key_by_section_key(the_gig_key.parent())
    the_gig = the_gig_key.get()
    
    the_plans=[]
    for the_section in the_members_by_section:
        section_plans=[]
        for a_member_key in the_section[1]:
            the_plan=plan.get_plan_for_member_for_gig(a_member_key.get(), the_gig)
            # add the plan to the list, but only if the member's section for this gig is this section
            if the_plan and the_plan.section == the_section[0]:
                section_plans.append( [a_member_key, the_plan] )
        the_plans.append( (the_section[0], section_plans) )
    
    the_archive_text = ""
    for a_section in the_plans:
        the_section_key = a_section[0]
        if (the_section_key):
            the_section_name=the_section_key.get().name
        else:
            the_section_name='None'
        the_archive_text = '{0}\n{1}'.format(the_archive_text,the_section_name)
        
        print 'section members is {0}'.format(a_section[1])
        for member_plans in a_section[1]:
            the_member = member_plans[0].get()
            the_plan = member_plans[1]
            the_archive_text = '{0}\n\t{1} {2} {3}'.format(the_archive_text,
                                                           the_member.name,
                                                           the_plan.value,
                                                           the_plan.comment)

            
    
    print '\n\n'
    print '{0}'.format(the_archive_text)
    print '\n\n'

#
#
# Handlers
#
#

class InfoPage(BaseHandler):
    """ class to serve the gig info page """

    @user_required
    def get(self):    
        self._make_page(self.user)

    def _make_page(self, the_user):

        # find the gig we're interested in
        gig_key_str = self.request.get("gk", None)
        if gig_key_str is None:
            self.response.write('no gig key passed in!')
            return # todo figure out what to do if there's no ID passed in

        gig_key = ndb.Key(urlsafe=gig_key_str)
        the_gig = gig_key.get()

        if the_gig is None:
            self.response.write('did not find a gig!')
            return # todo figure out what to do if we didn't find it
            
        debug_print('found gig object: {0}'.format(the_gig.title))

        the_band_key = the_gig.key.parent()

        the_members_by_section = band.get_member_keys_of_band_key_by_section_key(the_band_key)

        the_plans=[]
        for the_section in the_members_by_section:
            section_plans=[]
            for a_member_key in the_section[1]:
                the_plan=plan.get_plan_for_member_for_gig(a_member_key.get(), the_gig)
                # add the plan to the list, but only if the member's section for this gig is this section
                if the_plan and the_plan.section == the_section[0]:
                    section_plans.append( [a_member_key, the_plan] )
            the_plans.append( (the_section[0], section_plans) )

                
        template_args = {
            'title' : 'Gig Info',
            'gig' : the_gig,
            'member_plans' : the_plans,
            'get_sections_for_member_key_band_key' : member.get_sections_for_member_key_band_key,
            'nav_info' : member.nav_info(the_user, None)
        }
        self.render_template('gig_info.html', template_args)


class EditPage(BaseHandler):
    """ A class for rendering the gig edit page """

    @user_required
    def get(self):
        self._make_page(self.user)

    def _make_page(self, the_user):

        if self.request.get("new", None) is not None:
            the_gig = None
            is_new = True
        else:
            the_gig_key = self.request.get("gk", None)
            if (the_gig_key is None):
                return # figure out what to do
                
            the_gig = ndb.Key(urlsafe=the_gig_key).get()
            if the_gig is None:
                self.response.write('did not find a band or gig!')
                return # todo figure out what to do if we didn't find it
            debug_print('found gig object: {0}'.format(the_gig.title))
            is_new = False
                    
        template_args = {
            'title' : 'Gig Edit',
            'gig' : the_gig,
            'all_bands' : member.get_bands_of_member(the_user),
            'nav_info' : member.nav_info(the_user, None),
            'newgig_is_active' : is_new
        }
        self.render_template('gig_edit.html', template_args)
        
        
    def post(self):
        """post handler - if we are edited by the template, handle it here 
           and redirect back to info page"""


        the_gig_key = self.request.get("gk", '0')
        
        if (the_gig_key == '0'):
            the_gig = None
        else:
            the_gig = ndb.Key(urlsafe=the_gig_key).get()

        # first, get the band
        gig_is_new = False
        gig_band_key = self.request.get("gig_band", None)
        if gig_band_key is not None and gig_band_key != '':
            the_band = ndb.Key(urlsafe=gig_band_key).get()
            if the_gig is None:
                the_gig = new_gig(title="tmp", the_band=the_band)
                gig_is_new = True

        # now get the info
        gig_title = self.request.get("gig_title", None)
        if gig_title is not None and gig_title != '':
            the_gig.title = gig_title
        
        gig_details = self.request.get("gig_details", None)
        if gig_details is not None and gig_details != '':
            the_gig.details = gig_details

        gig_setlist = self.request.get("gig_setlist", None)
        if gig_setlist is not None and gig_setlist != '':
            the_gig.setlist = gig_setlist

        gig_date = self.request.get("gig_date", None)
        if gig_date is not None and gig_date != '':
            the_gig.date = datetime.datetime.strptime(gig_date, \
                                                      '%m/%d/%Y').date()
            # todo validate form entry so date isn't bogus
       
        the_gig.put()            

        if gig_is_new:
            goemail.announce_new_gig(the_gig, self.uri_for('gig_info', _full=True, gk=the_gig.key.urlsafe()))

        return self.redirect(\
            '/gig_info.html?&gk={0}'.format(the_gig.key.urlsafe()))
                
class DeleteHandler(BaseHandler):
    def get(self):

        user = self.user
        
        if user is None:
            self.redirect(users.create_login_url(self.request.uri))
        else:
            the_gig_key = self.request.get("gk", None)

            if the_gig_key is None:
                self.response.write('did not find gig!')
            else:
                the_gig = ndb.Key(urlsafe=the_gig_key).get()
                plan.delete_plans_for_gig(the_gig)            
                the_gig.key.delete()
            return self.redirect('/agenda.html')
            
class PrintSetlist(BaseHandler):
    """ print-friendly setlist view """
    
    @user_required
    def get(self):
        self._make_page(self.user)

    def _make_page(self, the_user):

        the_gig_key = self.request.get("gk", '0')
        
        if (the_gig_key == '0'):
            return # todo what else to do?
        else:
            the_gig = ndb.Key(urlsafe=the_gig_key).get()

        template_args = {
            'the_gig' : the_gig,
        }
        self.render_template('print_setlist.html', template_args)
        
class ArchiveHandler(BaseHandler):
    """ archive this gig, baby! """
            
    @user_required
    def get(self):

        # find the gig we're interested in
        gig_key_str = self.request.get("gk", None)
        if gig_key_str is None:
            self.response.write('no gig key passed in!')
            return # todo figure out what to do if there's no ID passed in
            
        the_gig_key=ndb.Key(urlsafe=gig_key_str)
        if the_gig_key:
            make_archive_for_gig_key(the_gig_key)

        return self.redirect('/gig_info.html?gk={0}'.format(gig_key_str))
        
