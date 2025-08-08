from datetime import datetime, timedelta
import random

from sqlalchemy import text

from .db import engine


def main():
    ddl = [
        """
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL
        );
        """,
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(customer_id) REFERENCES customers(id)
        );
        """,
    ]

    with engine.begin() as conn:
        for stmt in ddl:
            conn.exec_driver_sql(stmt)

        # Seed customers
        cities = ["New York", "San Francisco", "London", "Berlin", "Tokyo"]
        names = [
            "Acme Corp", "Globex", "Initech", "Umbrella", "Stark Industries",
            "Wayne Enterprises", "Soylent", "Wonka", "Hooli", "Pied Piper"
        ]
        # Clear existing
        conn.exec_driver_sql("DELETE FROM orders;")
        conn.exec_driver_sql("DELETE FROM customers;")

        for i, name in enumerate(names, start=1):
            city = random.choice(cities)
            conn.exec_driver_sql("INSERT INTO customers (id, name, city) VALUES (?, ?, ?);", (i, name, city))

        now = datetime.utcnow()
        order_id = 1
        for cust_id in range(1, len(names) + 1):
            for _ in range(random.randint(5, 20)):
                amount = round(random.uniform(20, 5000), 2)
                created_at = (now - timedelta(days=random.randint(0, 180))).isoformat()
                conn.exec_driver_sql(
                    "INSERT INTO orders (id, customer_id, amount, created_at) VALUES (?, ?, ?, ?);",
                    (order_id, cust_id, amount, created_at),
                )
                order_id += 1

    print("Bootstrap complete. Sample tables: customers, orders")


if __name__ == "__main__":
    main()