import operator


def generate_table_html(table):
    """
    Генерирует HTML-код для таблицы на основе данных из переданного списка словарей.

    :param table: список словарей с данными для таблицы
    :return: строка с HTML-кодом для таблицы
    """
    rows = []
    for row in table:
        rows.append(f"<tr><td>{row['Organization']}</td><td>{row['ACC']}</td>"
                    f"<td style='text-align: center;'>{row['Balance IN']}</td>"
                    f"<td style='text-align: center;'>{row['Credit']}</td>"
                    f"<td style='text-align: center;'>{row['Debit']}</td>"
                    f"<td style='text-align: center;'>{row['Balance OUT']}</td></tr>")
    return "".join(rows)


def generate_report_html(table, data_start, data_end=None):
    """
    Генерирует HTML-код для отчета на основе переданных данных.

    :param table: список словарей с данными для таблицы
    :param data_start: дата начала периода, за который составляется отчет
    :param data_end: дата конца периода, за который составляется отчет (опционально)
    :return: строка с HTML-кодом для отчета
    """
    table.sort(key=operator.itemgetter('Organization'))

    # Определяем заголовок отчета в зависимости от наличия даты окончания периода
    if data_end:
        title = f"Звіт за період з {data_start} по {data_end}"
    else:
        title = f"Звіт за {data_start}"

    # Генерируем HTML-код для таблицы и всего отчета
    table_html = generate_table_html(table)
    html = f"""
        <html>
          <head></head>
          <body>
            <p>{title}</p>
            <table border="1">
              <tr>
                <th style="text-align: center;">Організація</th>
                <th style="text-align: center;">Рахунок</th>
                <th style="text-align: center;">Початковий залишок</th>
                <th style="text-align: center;">Надходження</th>
                <th style="text-align: center;">Вибуття</th>
                <th style="text-align: center;">Кінцевий залишок</th>
              </tr>
              {table_html}
            </table>
          </body>
        </html>
    """
    return html
