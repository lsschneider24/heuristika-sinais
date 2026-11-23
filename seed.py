import database

if __name__ == "__main__":
    database.init_db()
    database.seed_initial_data()
    stats = database.get_performance_stats()
    print(f"Banco inicializado com sucesso! Sinais totais: {stats['total_sinais']} | Taxa de acerto: {stats['taxa_acerto']}%")
