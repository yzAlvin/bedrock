import re

from django.conf import settings

import contentful as api
from rich_text_renderer import RichTextRenderer
from rich_text_renderer.text_renderers import BaseInlineRenderer


# Bedrock to Contentful locale map
LOCALE_MAP = {
    'de': 'de-DE',
}


class StrongRenderer(BaseInlineRenderer):
    @property
    def _render_tag(self):
        return 'strong'


def get_client():
    client = None
    if settings.CONTENTFUL_SPACE_ID:
        client = api.Client(
            settings.CONTENTFUL_SPACE_ID,
            settings.CONTENTFUL_SPACE_KEY,
            environment='V0',
            api_url=settings.CONTENTFUL_SPACE_API,
        )

    return client


def contentful_locale(locale):
    """Returns the Contentful locale for the Bedrock locale"""
    if locale.startswith('es-'):
        return 'es'

    return LOCALE_MAP.get(locale, locale)


def _get_height(width, aspect):
    height = 0
    if aspect == '1-1':
        height = width

    if aspect == '3-2':
        height = width * 0.6666

    if aspect == '16-9':
        height = width * 0.5625

    return round(height)


def _get_image_url(image, width, aspect):
    return 'https:' + image.url(
        w=width,
        h=_get_height(width, aspect),
        fit='fill',
        f='faces',
    )

def _get_product_class(product):
        product_themes = {
            'Firefox' : 'firefox',
            'Firefox Beta' : 'beta',
            'Firefox Developer' : 'developer',
            'Firefox Nightly' : 'nightly',
        }
        return 'mzp-t-product-' + product_themes[product] if product in product_themes else ''

def _get_abbr_from_width(width):
    widths = {
        'Extra Small' : 'xs',
        'Small' : 'sm',
        'Medium' : 'md',
        'Large' : 'lg',
        'Extra Large' : 'xl',
    }
    return widths[width] if width in widths else ''

def _get_width_class(width):
    width_abbr = _get_abbr_from_width(width)
    return 'mzp-t-content-' + width_abbr if width_abbr != '' else ''

def _get_theme_class(theme):
    return 'mzp-t-dark' if theme == "Dark" else ''


class ContentfulBase:
    def __init__(self):
        self.client = get_client()


class ContentfulUnfckPage(ContentfulBase):
    def get_page_data(self, page_id):
        page = self.client.entry(page_id, {'include': 3})
        return {
            'lang': page.lang.lower(),
            'cards': [self.get_card(c) for c in page.cards],
        }

    def get_card(self, card):
        card_data = {}
        for name, value in card.fields().items():
            if name == 'image':
                card_data['src_gif'] = 'https:' + value.url(w=280, h=280)
                card_data['src_high_res'] = 'https:' + value.url(w=350, h=350)
            else:
                card_data[name] = value

        return card_data


class ContentfulFirefoxPage(ContentfulBase):
    renderer = RichTextRenderer({
        'bold': StrongRenderer,
    })

    def get_page_data(self, page_id, locale):
        locale = contentful_locale(locale)
        page = self.client.entry(page_id, {'locale': locale})
        headlines = {}
        for name, value in page.fields().items():
            if isinstance(value, dict):
                value = self.renderer.render(value)

            headlines[name] = value

        return {'headlines': headlines}


class ContentfulHomePage(ContentfulBase):
    renderer = RichTextRenderer({
        'bold': StrongRenderer,
    })
    client = None
    card_field_re = re.compile(r'card\d$')
    card_fields = [
        'title',
        'desc',
        'cta',
        'meta',
        'image_url',
        'link_url',
        'tag_label',
        'youtube_id',
    ]
    # size, aspect
    card_layouts = {
        'sixCardLayout': [
            ('small', '3-2'),
            ('small', '3-2'),
            ('small', '3-2'),
            ('small', '3-2'),
            ('small', '3-2'),
            ('small', '3-2'),
        ],
        'fiveCardLayout': [
            ('large', '16-9'),
            ('small', '1-1'),
            ('small', '3-2'),
            ('small', '3-2'),
            ('small', '3-2'),
        ],
        'fourCardLayout': [
            ('extra-small', '16-9'),
            ('extra-small', '16-9'),
            ('extra-small', '16-9'),
            ('extra-small', '16-9'),
        ],
        'threeCardLayout': [
            ('small', '1-1'),
            ('small', '3-2'),
            ('small', '1-1'),
        ],
        'twoCardLayout': [
            ('medium', '3-2'),
            ('medium', '3-2'),
        ],
    }
    # normal, high-res
    card_image_widths = {
        'extra-small': (450, 900),
        'small': (450, 900),
        'medium': (600, 1200),
        'large': (930, 1860),
    }
    card_layout_classes = {
        'sixCardLayout': 'third',
        'fiveCardLayout': 'hero',
        'fourCardLayout': 'quarter',
        'threeCardLayout': 'third',
        'twoCardLayout': 'half',
    }

    def get_all_page_data(self):
        pages = self.client.entries({'content_type': 'pageGeneral'})
        return [self.get_page_data(p.id) for p in pages]

    # page entry
    def get_entry_data(self, page_id):
        entry_data = self.client.entry(page_id)
        # print(entry_data.__dict__)
        return entry_data

    def get_page_data(self, page_id):
        layouts = []
        page = self.client.entry(page_id, {'include': 5})
        page_data = {
            'id': page.id,
            'content_type': page.content_type.id,
        }
        layouts_data = self.get_page_layouts(page)
        for layout in layouts_data:
            layout_data = {
                'type': layout.content_type.id,
                'class': self.card_layout_classes[layout.content_type.id],
            }
            cards = self.get_layout_cards(layout)
            layout_data['cards'] = self.get_card_dicts(cards, layout_data['type'])
            layouts.append(layout_data)

        page_data['layouts'] = layouts
        return page_data

    def make_slug(self, url):
        slug = url
        # remove trailing slash
        if slug.rfind('/') == (len(slug) - 1):
            slug = slug[:-1]

        #remove folder names
        if slug.rfind('/') > -1:
            slug = slug[(slug.rfind('/') + 1):]

        return slug

    def get_info_data(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()

        preview_image_url = fields['preview_image'].fields().get('file').get('url')

        info_data = {
            'title': fields['preview_title'],
            'blurb': fields['preview_blurb'],
            'image': 'https:' + preview_image_url,
            'slug': self.make_slug(fields['url']),
        }
        return info_data

    def get_page_layouts(self, page_obj):
        return [v for k, v in page_obj.fields().items() if k.startswith('card_group')]

    def get_layout_cards(self, layout):
        return [v for k, v in layout.fields().items() if self.card_field_re.match(k)]

    def get_card_dicts(self, cards, layout_type):
        config = self.card_layouts[layout_type]
        card_list = []
        for i, card in enumerate(cards):
            size, aspect = config[i]
            card_list.append(self.get_card(card, size, aspect))

        return card_list

    def get_card(self, card, size, aspect):
        if hasattr(card, 'card'):
            card = card.card

        if 'aspect_ratio' in card.fields():
            aspect = card.aspect_ratio.replace('x', '-')

        card_data = {
            'class': f'mzp-c-card-{size}',
            'aspect_ratio': f'mzp-has-aspect-{aspect}',
        }
        for name, value in card.fields().items():
            if name in self.card_fields:
                if name == 'image_url':
                    width, width_highres = self.card_image_widths[size]
                    max_width = value.file['details']['image']['width']
                    if max_width >= width_highres:
                        card_data['highres_image_url'] = _get_image_url(value, width_highres, aspect)

                    card_data[name] = _get_image_url(value, width, aspect)
                    continue

                card_data[name] = value

                if name == 'title':
                    card_data['ga_title'] = value

                if name == 'youtube_id':
                    card_data['media_icon'] = 'mzp-has-video'

        return card_data

    def get_body(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()
        body = fields['body']
        page_body = self.renderer.render(body)

        return page_body

    def get_hero_data(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()
        if 'component_hero' in fields:
            hero_obj = fields['component_hero']
            hero_fields = hero_obj.fields()
            hero_image_url = hero_fields['image'].fields().get('file').get('url')
            hero_body = self.renderer.render(hero_fields.get('body'))

            hero_data = {
                'theme_class': _get_theme_class(hero_fields.get('theme')),
                'product_class': _get_product_class(hero_fields.get('product_icon')),
                'title': hero_fields.get('heading'),
                'tagline': hero_fields.get('tagline'),
                'body': hero_body,
                'image': 'https:' + hero_image_url,
            }
        else:
            hero_data = {}

        return hero_data

    # any entry
    def get_entry_by_id(self, entry_id):
        return self.client.entry(entry_id)

    def get_callout_data(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()

        if 'layout_callout' in fields:
            callout_layout_obj = fields['layout_callout']
            callout_layout_fields = callout_layout_obj.fields()

            callout_component_id = callout_layout_fields.get('component_callout').id
            callout_component_obj = self.get_entry_by_id(callout_component_id)
            callout_component_fields = callout_component_obj.fields()

            callout_data = {
                'theme_class': _get_theme_class(callout_layout_fields.get('theme')),
                'product_class': _get_product_class(callout_component_fields.get('product_icon')),
                'title': callout_component_fields.get('heading'),
                'body': callout_component_fields.get('body'),
            }
        else:
            callout_data = {}

        return callout_data



class ContentfulPage(ContentfulBase):
    #TODO: List: stop list items from being wrapped in paragraph tags
    #TODO: List: add class to lists to format
    #TODO: If last item in content is a p:only(a) add cta link class?
    renderer = RichTextRenderer({
        'bold': StrongRenderer,
    })
    client = None

    def get_all_page_data(self):
        pages = self.client.entries({'content_type': 'pageVersatile'})
        return [self.get_page_data(p.id) for p in pages]

    def get_page_data(self, page_id):
        layouts = []
        page = self.client.entry(page_id, {'include': 5})
        page_data = {
            'id': page.id,
            'content_type': page.content_type.id,
        }
        return page_data

    # page entry
    def get_entry_data(self, page_id):
        entry_data = self.client.entry(page_id)
        # print(entry_data.__dict__)
        return entry_data

    # any entry
    def get_entry_by_id(self, entry_id):
        return self.client.entry(entry_id)

    def get_info_data(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()

        info_data = {
            'title': fields['preview_title'],
            'blurb': fields['preview_blurb'],
            'slug': fields['slug'],
        }

        if 'preview_image' in fields:
            preview_image_url = fields['preview_image'].fields().get('file').get('url')
            info_data['image'] = 'https:' + preview_image_url

        return info_data


    # def get_content(self, page_id):
    #     page_obj = self.client.entry(page_id)
    #     fields = page_obj.fields()
    #     print(fields)

    #     entries = []
    #     # look through all entries and find content ones
    #     for key, value in fields.items():
    #         if key == 'component_hero':
    #             entries.append(self.get_hero_data(value.id))
    #         elif key == 'body':
    #             entries.append(self.get_text_data(value))
    #         elif key == 'layout_callout':
    #             entries.append(self.get_callout_data(value.id))

    #     return entries


    def get_content(self, page_id):
        page_obj = self.client.entry(page_id)
        fields = page_obj.fields()
        content = fields.get('content')
        #print(content)

        entries = []
        # get components from content
        for item in content:
            content_type = item.sys.get('content_type').id
            if content_type == 'componentHero':
                entries.append(self.get_hero_data(item.id))
            elif content_type == 'layoutCallout':
                entries.append(self.get_callout_data(item.id))

        return entries

    def get_text_data(self, value):
        text_data = {
            'component': 'text',
            'body': self.renderer.render(value),
            'width_class': _get_width_class('Medium') #TODO
        }

        return text_data

    def get_hero_data(self, hero_id):
        hero_obj = self.get_entry_by_id(hero_id)
        fields = hero_obj.fields()

        hero_image_url = fields['image'].fields().get('file').get('url')
        hero_reverse = fields.get('image_position')
        hero_body = self.renderer.render(fields.get('body'))

        hero_data = {
            'component': 'hero',
            'theme_class': _get_theme_class(fields.get('theme')),
            'product_class': _get_product_class(fields.get('product_icon')),
            'title': fields.get('heading'),
            'tagline': fields.get('tagline'),
            'body': hero_body,
            'image': 'https:' + hero_image_url,
            'image_position': fields.get('image_position'),
            'image_class': 'mzp-l-reverse' if hero_reverse == 'Left' else '',
            'cta': self.get_cta_data(fields.get('cta').id) if fields.get('cta') else {'include_cta': False,}
        }

        #print(hero_data)

        return hero_data

    def get_callout_data(self, callout_id):
        config_obj = self.get_entry_by_id(callout_id)
        config_fields = config_obj.fields()

        content_id = config_fields.get('component_callout').id
        content_obj = self.get_entry_by_id(content_id)
        content_fields = content_obj.fields()
        content_body = self.renderer.render(content_fields.get('body'))

        callout_data = {
            'component': 'callout',
            'theme_class': _get_theme_class(config_fields.get('theme')),
            'product_class': _get_product_class(content_fields.get('product_icon')),
            'title': content_fields.get('heading'),
            'body': content_body,
        }

        return callout_data

    def get_cta_data(self, cta_id):
        cta_obj = self.get_entry_by_id(cta_id)
        cta_fields = cta_obj.fields()

        cta_data = {
            'component': cta_obj.sys.get('content_type').id,
            'label': cta_fields.get('label'),
            'action': cta_fields.get('action'),
            'size': 'mzp-t-xl',  #TODO
            'theme': 'mzp-t-primary',  #TODO
            'include_cta': True,
        }
        return cta_data


contentful_home_page = ContentfulPage()
contentful_unfck_page = ContentfulUnfckPage()
contentful_firefox_page = ContentfulFirefoxPage()


#TODO make optional fields optional
