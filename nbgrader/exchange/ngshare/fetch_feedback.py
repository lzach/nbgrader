#!/usr/bin/python
# -*- coding: utf-8 -*-
import os
import shutil
import glob

from nbgrader.exchange.abc import ExchangeFetchFeedback as ABCExchangeFetchFeedback
from nbgrader.exchange.ngshare import Exchange

from nbgrader.utils import check_mode, notebook_hash, make_unique_key, \
    get_username
from nbgrader.utils import parse_utc
import requests


# /api/feedback/course1/challenge/Lawrence

class ExchangeFetchFeedback(Exchange, ABCExchangeFetchFeedback):

    def init_src(self):
        if self.coursedir.course_id == '':
            self.fail('No course id specified. Re-run with --course flag.')

        if self.coursedir.student_id != '*':

            # An explicit student id has been specified on the command line; we use it as student_id
            if '*' in self.coursedir.student_id or '+' in self.coursedir.student_id:
                self.fail("The student ID should contain no '*' nor '+'; got {}".format(self.coursedir.student_id))
            student_id = self.coursedir.student_id
        else:
            student_id = get_username()
        self.cache_path = os.path.join(self.cache,
                self.coursedir.course_id)
        assignment_id = (self.coursedir.assignment_id if self.coursedir.assignment_id else '*')
        pattern = os.path.join(self.cache_path, '*+{}+*'.format(assignment_id))
        self.log.debug('Looking for submissions with pattern: {}'.format(pattern))

        self.src_path = self.ngshare_url + '/api/feedback/{}/{}/{}'.format(self.coursedir.course_id, assignment_id, self.username)

        self.timestamps = []
        submissions = [os.path.split(x)[-1] for x in glob.glob(pattern)]
        for submission in submissions:
            (_, assignment_id, timestamp) = submission.split('/')[-1].split('+')
            self.timestamps.append(timestamp)

        self.log.info(self.timestamps)

    def init_dest(self):
        if self.path_includes_course:
            root = os.path.join(self.coursedir.course_id, self.coursedir.assignment_id)
        else:
            root = self.coursedir.assignment_id
        self.dest_path = os.path.abspath(os.path.join(self.assignment_dir, root, 'feedback'))

    def copy_files(self):
        self.log.info('Fetching feedback from server')
        if len(self.timestamps) == 0:
            self.log.info('No feedback available to fetch for your submissions')

        self.log.info(self.timestamps)
        for timestamp in self.timestamps:
            imestamp = parse_utc(timestamp)
            params = {'timestamp': timestamp, 'list_only': 'false', 'user': self.username}

            try:
                response = requests.get(self.src_path, params=params)
            except:
                self.log.warn('An error occurred while trying to fetch feedback for {}'.format(self.coursedir.assignment_id))

            if response.status_code != requests.codes.ok:
                self.log.warn('An error occurred while trying to fetch feedback for {}'.format(self.coursedir.assignment_id))
            elif not response.json()['success']:
                self.log.warn('An error occurred while trying to fetch feedback for {}'.format(self.coursedir.assignment_id))
                self.log.warn('Reason: {}'.format(response.json()['message']))
            elif response.json()['success']:
                self.log.info(self.dest_path)
                try:
                    self.decode_dir(response.json()['files'], self.dest_path)
                    self.log.info('Successfully decoded feedback for {} saved to {}'.format(self.coursedir.assignment_id, self.dest_path))
                except:
                    self.log.warn('Could not decode the feedback')
