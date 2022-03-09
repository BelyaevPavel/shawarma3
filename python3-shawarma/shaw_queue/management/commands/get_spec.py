from django.core.management.base import BaseCommand, CommandError
from shaw_queue.models import ProductOption, ProductVariant, MacroProduct, MacroProductContent, ContentOption, \
    SizeOption, Menu
import csv


class Command(BaseCommand):
    help = 'Prints tabulated new menu'

    def handle(self, *args, **options):
        content_option = MacroProductContent.objects.get(title__iexact='Люля-Кебаб говядина')
        macro_product = MacroProduct.objects.get(title__iexact='Люля-кебаб')
        size_option = SizeOption.objects.get(title__iexact='Стандартный')
        with open('NewMenuRelations.csv', 'w') as csvfile:
            fieldnames = ['macro_product', 'macro_product_content', 'content_option', 'product_variant', 'menu_item',
                          'size_option']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            product_variants = ProductVariant.objects.filter(macro_product_content=content_option,
                                                             size_option=size_option)
            for product_variant in product_variants:
                writer.writerow({'macro_product': macro_product.title,
                                 'macro_product_content': content_option.title,
                                 'content_option': content_option.content_option.title,
                                 'product_variant': product_variant.title,
                                 'menu_item': product_variant.menu_item.title,
                                 'size_option': size_option.title})
                print("MP: {}; MPC: {}; CO: {}; PV: {}; PVMI: {}; SO: {}; \n".format(
                    macro_product.title, content_option.title, content_option.content_option.title,
                    product_variant.title, product_variant.menu_item.title, size_option.title))
                # self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))
