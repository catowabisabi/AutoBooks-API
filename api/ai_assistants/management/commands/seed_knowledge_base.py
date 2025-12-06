"""
Management command to seed the knowledge base with bilingual data.
Loads knowledge base entries from JSON file.
"""
import json
import os
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Seed knowledge base with bilingual (EN/ZH) data from JSON file'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='ai_assistants/data/knowledge_base.json',
            help='Path to knowledge base JSON file (relative to api folder)'
        )

    def handle(self, *args, **options):
        # Get the JSON file path
        base_dir = settings.BASE_DIR
        json_file = os.path.join(base_dir, options['file'])
        
        if not os.path.exists(json_file):
            self.stderr.write(
                self.style.ERROR(f'Knowledge base file not found: {json_file}')
            )
            return
        
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            knowledge_data = json.load(f)
        
        self.stdout.write(f'Loaded {len(knowledge_data)} knowledge base entries')
        
        # Display summary by category
        categories = {}
        for item in knowledge_data:
            cat = item.get('category', 'general')
            categories[cat] = categories.get(cat, 0) + 1
        
        self.stdout.write('\nEntries by category:')
        for cat, count in sorted(categories.items()):
            self.stdout.write(f'  - {cat}: {count}')
        
        # Display sample entries
        self.stdout.write('\nSample entries:')
        for item in knowledge_data[:3]:
            self.stdout.write(
                self.style.SUCCESS(f"  [{item['id']}] EN: {item['title_en']}")
            )
            self.stdout.write(
                self.style.SUCCESS(f"         ZH: {item['title_zh']}")
            )
        
        self.stdout.write(
            self.style.SUCCESS('\nKnowledge base data loaded successfully!')
        )
        self.stdout.write(
            'The RAG service will automatically load this data from the JSON file.'
        )
