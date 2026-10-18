"""Safe local diagnostics: excludes credentials and unrelated HA states."""
import json
from django.core.management.base import BaseCommand, CommandError
from dashboard.services.home_assistant import HomeAssistant, HAError, FIELDS

class Command(BaseCommand):
    help = 'Verify HA authentication, ANMA entity mappings, current readings and 24-hour history.'

    def handle(self,*args,**options):
        try:
            service=HomeAssistant()
            if not service.authenticate():
                raise HAError('unexpected_api_response')
            states=service.states()
            entities=service.discover(states)
            current=service.snapshot()
            history=service.history()
            report={'authenticated':True,'entity_count':len(entities),'entities':entities,
                    'mapping':service.mapping(states),'current':current,
                    'history':{k:v for k,v in history.items() if k!='series'},
                    'history_points':len(history['series']),
                    'first_recorded_point':next((r['timestamp'] for r in history['series'] if any(r[k] is not None for k in ['pv','load','grid','battery','soc'])),None)}
            self.stdout.write(json.dumps(report,ensure_ascii=False,indent=2))
        except HAError as exc:
            raise CommandError('Home Assistant: '+exc.code) from None
