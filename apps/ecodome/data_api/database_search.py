import logging
from apps.core.db import create_database_engine, create_session
from sqlalchemy import select, func
from apps.core.models.product import Product, MarketPlaceProduct

engine = create_database_engine()
session = create_session(engine)

"""
CREATE INDEX trigram_index ON {model.__tablename__} USING GIN(search_vector gin_trgm_ops)
"""

def nlp():
    pass

def search_database_by_labels(labels, model=Product):
    try:
        all_rows = session.query(model).all()
        results = []
        for label in labels:
            query = (
                select([model]).
                where(func.similarity(model.label_column, label) > 0.3).
                order_by(func.similarity(model.label_column, label).desc())
            )
            result_rows = session.execute(query).fetchall()
            for row in result_rows:
                label_tokens = nlp(label.lower())
                label_column_tokens = nlp(row.label_column.lower())
                similarity_score = label_tokens.similarity(label_column_tokens)
                fuzzy_score = fuzz.token_set_ratio(label.lower(), row.label_column.lower())
                confidence_score = (similarity_score + fuzzy_score) / 2
                if confidence_score > 70:
                    result_entry = {
                        "label": label,
                        "result_id": row.id,
                        "label_column": row.label_column,
                        "confidence_score": confidence_score
                    }
                    results.append(result_entry)

        return results
    except Exception as e:
        logging.error(f"Error : {e}")
        return None
    
"""
def search_database_by_labels(labels, model):
    try:
        # Create a session
        session = Session()

        # Create trigram index for search_vector
        session.execute(f"CREATE INDEX trigram_index ON {model.__tablename__} USING GIN(search_vector gin_trgm_ops)")

        results = []
        for label in labels:
            # Tokenize the label using spaCy
            label_tokens = nlp(label.lower())

            # Tokenize the label_column using spaCy
            model_search_vector = func.to_tsvector(model.label_column)
            label_column_tokens = func.to_tsquery(label.lower())

            # Calculate rank using ts_rank_cd function
            rank = func.ts_rank_cd(model_search_vector, label_column_tokens, 32)

            # Construct the SQLAlchemy query for the database search
            query = select([model]).where(model.search_vector.match(label))

            # Execute the query and fetch all results, ordered by rank
            result_rows = session.execute(query.order_by(rank.desc())).fetchall()

            for row in result_rows:
                result_entry = {
                    "label": label,
                    "result_id": row.id,
                    "label_column": row.label_column,
                    "rank": rank
                }
                results.append(result_entry)

        return results

    except Exception as e:
        print(f"Error: {e}")
        return None

    finally:
        # Close the session
        if session:
            session.close()
"""