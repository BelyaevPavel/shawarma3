from django.core.management.base import BaseCommand, CommandError
from shaw_queue.models import ProductOption, ProductVariant, MacroProduct, MacroProductContent, ContentOption, \
    SizeOption, Menu
import csv


class Command(BaseCommand):
    help = 'Prints tabulated new menu'

    def handle(self, *args, **options):
        with open('NewMenuRelations.csv', 'w') as csvfile:
            fieldnames = ['macro_product', 'macro_product_content', 'content_option', 'product_variant', 'menu_item',
                          'size_option', 'product_option_menu_item']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            macro_products = MacroProduct.objects.all()
            for macro_product in macro_products:
                macro_product_contents = MacroProductContent.objects.filter(macro_product=macro_product)
                for macro_product_content in macro_product_contents:
                    content_option = macro_product_content.content_option
                    product_variants = ProductVariant.objects.filter(macro_product_content=macro_product_content)
                    for product_variant in product_variants:
                        size_option = product_variant.size_option
                        product_options = ProductOption.objects.filter(product_variants=product_variant)
                        for product_option in product_options:
                            product_option_menu_item = product_option.menu_item

                            writer.writerow({'macro_product': macro_product.title,
                                             'macro_product_content': macro_product_content.title,
                                             'content_option': content_option.title,
                                             'product_variant': product_variant.title,
                                             'menu_item': product_variant.menu_item.title,
                                             'size_option': size_option.title,
                                             'product_option_menu_item': product_option_menu_item.title})
                            print("MP: {}; MPC: {}; CO: {}; PV: {}; PVMI: {}; SO: {}; POMI: {}; \n".format(
                                macro_product.title, macro_product_content.title, content_option.title,
                                product_variant.title, product_variant.menu_item.title, size_option.title,
                                product_option_menu_item.title))
                            # self.stdout.write(self.style.SUCCESS('Successfully closed poll "%s"' % poll_id))
