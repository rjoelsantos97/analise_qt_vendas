import streamlit as st
import zipfile
import pandas as pd
from io import BytesIO

# Função para carregar e combinar os dados de todos os arquivos na pasta zipada
def load_and_combine_data(zip_file_path):
    data_frames = []
    with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
        for file_name in zip_ref.namelist():
            if file_name.endswith('.xlsx'):
                with zip_ref.open(file_name) as file:
                    df = pd.read_excel(file)
                    # Manter apenas as colunas relevantes, ajustando os nomes conforme necessário
                    rename_dict = {
                        'Ref': 'Referencia',
                        'Quantidade': 'Qtd Vendidas',
                        'DataDoc': 'Data da venda'
                        #'Zona': 'Zona'
                    }
                    # Ajustar colunas relevantes conforme disponível
                    relevant_columns = [col for col in ['Ref', 'Quantidade', 'DataDoc', 'Marca', 'Familia', 'LinhaProduto', 'Zona'] if col in df.columns]
                    df = df[relevant_columns]
                    df.rename(columns=rename_dict, inplace=True)
                    # Converter a coluna de data para datetime se existir
                    if 'Data da venda' in df.columns:
                        df['Data da venda'] = pd.to_datetime(df['Data da venda'], errors='coerce')
                    # Converter a coluna de quantidade para numérico, lidando com separadores de milhar
                    if 'Qtd Vendidas' in df.columns:
                        df['Qtd Vendidas'] = df['Qtd Vendidas'].astype(str).str.replace(',', '.').astype(float)
                    data_frames.append(df)
    combined_data = pd.concat(data_frames, ignore_index=True)
    return combined_data

# Função para identificar meses com vendas inferiores à média menos 1 unidade
def get_months_below_threshold(monthly_sales, avg_sales):
    below_threshold = []
    for ref in avg_sales['Referencia']:
        avg = avg_sales[avg_sales['Referencia'] == ref]['Qtd média mes'].values[0]
        threshold_value = avg - 1
        months_below = monthly_sales[(monthly_sales['Referencia'] == ref) & (monthly_sales['Qtd Vendidas'] < threshold_value)]
        below_threshold.append(", ".join(months_below['Mes'].astype(str).tolist()))
    return below_threshold

# Interface Streamlit
st.title("Análise de Vendas")

# Upload do arquivo ZIP
uploaded_file = st.file_uploader("Carregar arquivo ZIP contendo os dados de vendas", type="zip")
if uploaded_file is not None:
    # Carregar os dados
    data = load_and_combine_data(uploaded_file)

    # Verificar a presença de dados no dataset completo
    st.write(f"Total de registros no dataset completo: {len(data)}")

    # Parâmetros de Filtro
    start_date = st.date_input("Data de início", value=pd.to_datetime('2023-07-01'))
    end_date = st.date_input("Data de término", value=pd.to_datetime('2023-12-31'))

    marcas = st.multiselect("Marcas", options=data['Marca'].unique().tolist())
    familias = st.multiselect("Famílias", options=data['Familia'].unique().tolist())
    zonas = st.multiselect("Zonas", options=data['Zona'].unique().tolist())

    # Número de meses no período de análise
    num_months = ((end_date.year - start_date.year) * 12 + end_date.month - start_date.month) + 1

    # Filtrar os dados com base nas seleções de data
    filtered_data = data[
        (data['Data da venda'] >= start_date) &
        (data['Data da venda'] <= end_date)
    ]

    # Verificar se há registros após filtragem por data
    st.write(f"Total de registros após filtragem por data: {len(filtered_data)}")

    if 'Marca' in filtered_data.columns and marcas:
        filtered_data = filtered_data[filtered_data['Marca'].isin(marcas)]

    # Verificar se há registros após filtragem por marcas
    st.write(f"Total de registros após filtragem por marcas: {len(filtered_data)}")

    if 'Familia' in filtered_data.columns and familias:
        filtered_data = filtered_data[filtered_data['Familia'].isin(familias)]

    # Verificar se há registros após filtragem por famílias
    st.write(f"Total de registros após filtragem por famílias: {len(filtered_data)}")

    if 'Zona' in filtered_data.columns and zonas:
        filtered_data = filtered_data[filtered_data['Zona'].isin(zonas)]

    # Verificar se há registros após filtragem por zonas
    st.write(f"Total de registros após filtragem por zonas: {len(filtered_data)}")

    # Verificação se há registros após aplicação de todos os filtros
    if filtered_data.empty:
        st.write("Não há registros após aplicar todos os filtros.")
    else:
        st.write(f"Dados filtrados finais: {len(filtered_data)} registros encontrados.")

        # Agrupar os dados por mês e referência
        filtered_data['Mes'] = filtered_data['Data da venda'].dt.to_period('M')
        monthly_sales = filtered_data.groupby(['Referencia', 'Mes'])['Qtd Vendidas'].sum().reset_index()

        # Calcular a média mensal por referência considerando o número total de meses no período de análise
        total_sales = filtered_data.groupby('Referencia')['Qtd Vendidas'].sum().reset_index()
        total_sales.columns = ['Referencia', 'Vendas totais']
        total_sales['Qtd média mes'] = total_sales['Vendas totais'] / num_months

        # Identificar meses com vendas inferiores à média menos 1 unidade
        total_sales['Meses < média - 1 unidade'] = get_months_below_threshold(monthly_sales, total_sales)

        # Exibir o resultado completo
        st.write("Média mensal de vendas por referência e vendas totais:")
        st.dataframe(total_sales)

        # Exportar os resultados para um arquivo CSV
        csv = total_sales.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Baixar resultados como CSV",
            data=csv,
            file_name='average_monthly_sales_with_totals_and_analysis.csv',
            mime='text/csv',
        )
