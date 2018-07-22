from google.appengine.api import users

from requestmodel import *

import webapp2
import member
import gig
import plan
import band
import assoc
import json

from debug import debug_print
    
import datetime
from webapp2_extras import i18n
from webapp2_extras.i18n import gettext as _

class MainPage(BaseHandler):

    @user_required
    def get(self):    
        """ get handler for grid view """
        self._make_page(the_user=self.user)
            
    def _make_page(self,the_user):
        """ construct page for grid view """
        
        # find the bands this member is associated with
        if not the_user.is_superuser:
            the_assocs = assoc.get_confirmed_assocs_of_member(the_user)
            the_band_keys = [a.band for a in the_assocs]
        else:
            the_band_keys = band.get_all_bands(keys_only=True)
        
        if the_band_keys is None or len(the_band_keys)==0:
            return self.redirect('/member_info.html?mk={0}'.format(the_user.key.urlsafe()))
            
        # find the band we're interested in
        band_key_str=self.request.get("bk", None)
        if band_key_str is None:
            the_band_key = the_band_keys[0]
        else:
            the_band_key = ndb.Key(urlsafe=band_key_str)

        month_str=self.request.get("m",None)
        year_str=self.request.get("y",None)
        if month_str==None or year_str==None:
            start_date = datetime.datetime.now().replace(day=1)
        else:
            delta=0
            delta_str=self.request.get("d",None)
            if delta_str != None:
                delta=int(delta_str)
            year=int(year_str)
            month=int(month_str)
            month=month+delta
            if month>12:
                month = 1
                year = year+1
            if month<1:
                month=12
                year = year-1
            start_date = datetime.datetime(year=year, month=month, day=1)
        
        end_date = start_date
        if (end_date.month < 12):
            end_date = end_date.replace(month = end_date.month + 1, day = 1)
        else:
            end_date = end_date.replace(year = end_date.year + 1, month=1, day=1)

        show_canceled=True
        if the_user.preferences and the_user.preferences.hide_canceled_gigs:
            show_canceled=False

        the_gigs = gig.get_gigs_for_band_key_for_dates(the_band_key, start_date, end_date, get_canceled=show_canceled)

        all_plans = []
        for g in the_gigs:
            all_plans.append(plan.get_plans_for_gig_key(g.key))

        the_member_assocs = band.get_assocs_of_band_key_by_section_key(the_band_key, include_occasional=False)

        the_plans = {}
        for section in the_member_assocs:
            for an_assoc in section[1]:
                member_key = an_assoc.member
                member_plans = {}
                for i in range(0,len(the_gigs)):
                    gig_plans = all_plans[i]
                    for p in gig_plans:
                        if p.member == member_key:
                            member_plans[p.key.parent()] = p.value
                            break
                the_plans[member_key] = member_plans



        # the_plans = {}
        # for section in the_member_assocs:
        #     for an_assoc in section[1]:
        #         member_key=an_assoc.member
        #         member_plans = {}
        #         for a_gig in the_gigs:
        #             the_plan = plan.get_plan_for_member_key_for_gig_key(the_member_key=member_key, the_gig_key=a_gig.key, keys_only=True)
        #             if the_plan is not None:
        #                 member_plans[a_gig.key] = the_plan.get().value
        #         the_plans[member_key] = member_plans
                

        template_args = {
            'all_band_keys' : the_band_keys,
            'the_band_key' : the_band_key,
            'the_member_assocs_by_section' : the_member_assocs,
            'the_month_string' : member.format_date_for_member(the_user, start_date, 'month'),
            'the_month' : start_date.month,
            'the_year' : start_date.year,
            'the_date_formatter' : member.format_date_for_member,
            'the_gigs' : the_gigs,
            'the_plans' : the_plans,
            'grid_is_active' : True
        }
        self.render_template('grid.html', template_args)


# https://cloud.google.com/appengine/docs/standard/python/ndb/queries
class NewMainPage(BaseHandler):

    @user_required
    def get(self):    
        """ get handler for grid view """
        self._make_page(the_user=self.user)
            
    def _make_page(self,the_user):
        """ construct page for grid view """
        
        # find the bands this member is associated with
        if not the_user.is_superuser:
            the_assocs = assoc.get_confirmed_assocs_of_member(the_user)
            the_band_keys = [a.band for a in the_assocs]
        else:
            the_band_keys = band.get_all_bands(keys_only=True)
        
        if the_band_keys is None or len(the_band_keys)==0:
            return self.redirect('/member_info.html?mk={0}'.format(the_user.key.urlsafe()))
            
        # find the band we're interested in
        band_key_str=self.request.get("bk", None)
        if band_key_str is None:
            the_band_key = the_band_keys[0]
        else:
            the_band_key = ndb.Key(urlsafe=band_key_str)


        the_member_assocs = band.get_assocs_of_band_key_by_section_key(the_band_key, include_occasional=False)

        template_args = {
            'all_band_keys' : the_band_keys,
            'the_band_key' : the_band_key,
            'the_member_assocs_by_section' : the_member_assocs,
            'grid_is_active' : True,
            'start_month' : datetime.datetime.now().month,
            'start_year' : datetime.datetime.now().year,
        }
        self.render_template('newgrid.html', template_args)


class GridGigsHandler(BaseHandler):
    @user_required
    def post(self):
        the_user=self.user

        # find the band we're interested in
        band_key_str=self.request.get("bk", None)
        if band_key_str is None: 
            the_band_key = the_band_keys[0]
        else:
            the_band_key = ndb.Key(urlsafe=band_key_str)

        numstr=self.request.get("month", None)
        yearstr=self.request.get("year", None)

        if numstr is None or yearstr is None:
            start_date = datetime.datetime.now().replace(day=1)
            month_num = start_date.month
            year_num = start_date.year
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
        else:
            month_num = int(numstr)
            year_num = int(yearstr)
            year_add = 0
            if month_num > 12:
                month_num = 1
                year_num += 1
            elif month_num == 0:
                month_num = 12
                year_num -= 1
            start_date = datetime.datetime.now()
            start_date = start_date.replace(day=1, month=month_num, year=year_num, hour=0, minute=0, second=0, microsecond=0)


        end_date = start_date
        if (end_date.month < 12):
            end_date = end_date.replace(month = end_date.month + 1, day = 1)
        else:
            end_date = end_date.replace(year = end_date.year + 1, month=1, day=1)

        end_date = end_date - datetime.timedelta(days=1)

        show_canceled=True
        if the_user.preferences and the_user.preferences.hide_canceled_gigs:
            show_canceled=False

        the_gigs = gig.get_gigs_for_band_key_for_dates(the_band_key, start_date, end_date, get_canceled=show_canceled, get_archived=True)

        the_plans = []
        for a_gig in the_gigs:
            if (a_gig.is_archived is not True):
                plans = plan.get_plans_for_gig_key(a_gig.key)
                member_plans={}
                for a_plan in plans:
                    member_plans[a_plan.member.urlsafe()] = [a_plan.value, a_plan.member.get().name]
            else:
                member_plans={}

            the_plans.append({  'key': a_gig.key.urlsafe(), 
                                'title': a_gig.title, 
                                'date': make_grid_date_string(member.format_date_for_member, the_user, a_gig), 
                                'archived': a_gig.is_archived,
                                'status': a_gig.status,
                                'plans': member_plans })

        template_args= {
            'the_plans' : the_plans,
            'the_month' : month_num,
            'the_year' : year_num,
            'the_month_string' : '{0}<br>{1}<br>&nbsp;<br>&nbsp;'.format(member.format_date_for_member(the_user, start_date, 'month'),_('No Gigs!')),
        }
        self.response.write(json.dumps(template_args))
        # self.render_template('gridgigs.html', template_args)

def make_grid_date_string(the_date_formatter, the_user, gig):
    return '{0}<br>{1}'.format(the_date_formatter(the_user,gig.date,'short'),the_date_formatter(the_user,gig.date,'day'))

