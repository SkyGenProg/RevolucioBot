# -*- coding: utf-8 -*-

import os
import re
import json
import math
import argparse
import numpy as np
import pandas as pd
import tensorflow as tf

# -----------------------------
# Utils
# -----------------------------
def set_seed(seed=42):
    np.random.seed(seed)
    tf.random.set_seed(seed)

def basic_clean(s: str) -> str:
    if s is None or (isinstance(s, float) and math.isnan(s)):
        return ""
    s = str(s)
    # Nettoyage léger (garde la structure du diff)
    s = s.replace("\r", " ").replace("\n", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s

def compute_features(df: pd.DataFrame) -> pd.DataFrame:
    # Features très simples mais utiles
    old = df["old"].astype(str)
    new = df["new"].astype(str)
    diff = df["diff"].astype(str)

    df_feat = pd.DataFrame(index=df.index)

    df_feat["len_old"] = old.str.len()
    df_feat["len_new"] = new.str.len()
    df_feat["len_diff"] = diff.str.len()

    df_feat["delta_len"] = df_feat["len_new"] - df_feat["len_old"]
    df_feat["abs_delta_len"] = df_feat["delta_len"].abs()

    # Ratios (évite div0)
    df_feat["ratio_new_old"] = (df_feat["len_new"] + 1.0) / (df_feat["len_old"] + 1.0)
    df_feat["ratio_diff_new"] = (df_feat["len_diff"] + 1.0) / (df_feat["len_new"] + 1.0)

    # Nombre de caractères "suspects" (simple heuristique)
    df_feat["num_excl"] = new.str.count("!")
    df_feat["num_qm"] = new.str.count(r"\?")
    df_feat["num_caps"] = new.apply(lambda x: sum(1 for c in x if c.isupper()))
    df_feat["caps_ratio"] = df_feat["num_caps"] / (df_feat["len_new"] + 1.0)

    # Normalisation simple (z-score) sur les features numériques
    # (sera recalculée sur train uniquement plus bas)
    return df_feat

def make_tf_dataset(df, num_feat, batch_size=64, shuffle=False):
    inputs = {
        "old": df["old"].values,
        "new": df["new"].values,
        "diff": df["diff"].values,
        "num": num_feat.values.astype(np.float32),
    }
    labels = df["reverted"].values.astype(np.float32)

    ds = tf.data.Dataset.from_tensor_slices((inputs, labels))
    if shuffle:
        ds = ds.shuffle(min(len(df), 10000), reshuffle_each_iteration=True)
    ds = ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)
    return ds

# -----------------------------
# Model
# -----------------------------
def build_text_tower(name, vectorizer, input_dim, embed_dim=128, lstm_units=64, dropout=0.2):
    inp = tf.keras.Input(shape=(), dtype=tf.string, name=name)
    x = vectorizer(inp)
    x = tf.keras.layers.Embedding(input_dim=input_dim, output_dim=embed_dim, mask_zero=True)(x)
    x = tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(lstm_units, return_sequences=False))(x)
    x = tf.keras.layers.Dropout(dropout)(x)
    return inp, x

def build_model(num_features, vocab_size=50000, seq_len=400, embed_dim=128, lstm_units=64):
    vec_old = tf.keras.layers.TextVectorization(
        max_tokens=vocab_size, output_mode="int", output_sequence_length=seq_len
    )
    vec_new = tf.keras.layers.TextVectorization(
        max_tokens=vocab_size, output_mode="int", output_sequence_length=seq_len
    )
    vec_diff = tf.keras.layers.TextVectorization(
        max_tokens=vocab_size, output_mode="int", output_sequence_length=seq_len
    )

    # IMPORTANT: input_dim = max_tokens (vocab_size) + 2 dans certains cas,
    # mais TextVectorization respecte max_tokens, donc on peut utiliser vocab_size.
    # Pour être ultra sûr, on met vocab_size.
    inp_old, tower_old = build_text_tower("old", vec_old, input_dim=vocab_size, embed_dim=embed_dim, lstm_units=lstm_units)
    inp_new, tower_new = build_text_tower("new", vec_new, input_dim=vocab_size, embed_dim=embed_dim, lstm_units=lstm_units)
    inp_diff, tower_diff = build_text_tower("diff", vec_diff, input_dim=vocab_size, embed_dim=embed_dim, lstm_units=lstm_units)

    inp_num = tf.keras.Input(shape=(num_features,), dtype=tf.float32, name="num")
    x_num = tf.keras.layers.Dense(64, activation="relu")(inp_num)
    x_num = tf.keras.layers.Dropout(0.2)(x_num)

    x = tf.keras.layers.Concatenate()([tower_old, tower_new, tower_diff, x_num])
    x = tf.keras.layers.Dense(256, activation="relu")(x)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(64, activation="relu")(x)
    out = tf.keras.layers.Dense(1, activation="sigmoid", name="reverted")(x)

    model = tf.keras.Model(inputs=[inp_old, inp_new, inp_diff, inp_num], outputs=out)
    model.compile(
        optimizer=tf.keras.optimizers.Adam(1e-4),
        loss=tf.keras.losses.BinaryCrossentropy(),
        metrics=[tf.keras.metrics.AUC(name="auc"),
                 tf.keras.metrics.Precision(name="precision"),
                 tf.keras.metrics.Recall(name="recall")]
    )
    return model, vec_old, vec_new, vec_diff

# -----------------------------
# Main
# -----------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default="model/vikidia_fr/rc_wiki.csv", help="Chemin vers le CSV")
    parser.add_argument("--outdir", default="model_vandalism", help="Dossier de sortie")
    parser.add_argument("--batch", type=int, default=64)
    parser.add_argument("--epochs", type=int, default=10)
    parser.add_argument("--vocab", type=int, default=50000)
    parser.add_argument("--seqlen", type=int, default=400)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    set_seed(args.seed)
    os.makedirs(args.outdir, exist_ok=True)

    df = pd.read_csv(args.csv)

    # Champs requis
    required = ["old", "new", "diff", "reverted"]
    for c in required:
        if c not in df.columns:
            raise ValueError(f"Colonne manquante: {c}")

    # Nettoyage texte
    for col in ["old", "new", "diff"]:
        df[col] = df[col].apply(basic_clean)

    # Label
    df["reverted"] = pd.to_numeric(df["reverted"], errors="coerce").fillna(0).astype(int)

    # Drop lignes vides totales
    df = df.dropna(subset=["reverted"])

    # Split (stratifié simple)
    df = df.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)

    y = df["reverted"].values
    pos = (y == 1).sum()
    neg = (y == 0).sum()
    print(f"Rows={len(df)}  pos={pos}  neg={neg}  pos_rate={pos/len(df):.3f}")

    n = len(df)
    n_train = int(n * 0.8)
    n_val = int(n * 0.1)

    df_train = df.iloc[:n_train].copy()
    df_val = df.iloc[n_train:n_train + n_val].copy()
    df_test = df.iloc[n_train + n_val:].copy()

    # Features numériques
    feat_train = compute_features(df_train)
    feat_val = compute_features(df_val)
    feat_test = compute_features(df_test)

    # Normalisation basée train uniquement
    mean = feat_train.mean(axis=0)
    std = feat_train.std(axis=0).replace(0, 1.0)

    feat_train = (feat_train - mean) / std
    feat_val = (feat_val - mean) / std
    feat_test = (feat_test - mean) / std

    # TF datasets
    ds_train = make_tf_dataset(df_train, feat_train, batch_size=args.batch, shuffle=True)
    ds_val = make_tf_dataset(df_val, feat_val, batch_size=args.batch, shuffle=False)
    ds_test = make_tf_dataset(df_test, feat_test, batch_size=args.batch, shuffle=False)

    # Modèle + vectorizers
    num_features = feat_train.shape[1]
    model, vec_old, vec_new, vec_diff = build_model(
        num_features=num_features,
        vocab_size=args.vocab,
        seq_len=args.seqlen
    )

    # Adapt vocabularies sur train
    vec_old.adapt(df_train["old"].values)
    vec_new.adapt(df_train["new"].values)
    vec_diff.adapt(df_train["diff"].values)

    # Gestion du déséquilibre (optionnel mais souvent utile)
    # class_weight = {0: 1.0, 1: neg / max(pos, 1)}
    # print("class_weight:", class_weight)

    callbacks = [
        tf.keras.callbacks.EarlyStopping(monitor="val_auc", mode="max", patience=2, restore_best_weights=True),
        tf.keras.callbacks.ModelCheckpoint(
            filepath=os.path.join(args.outdir, "ckpt.keras"),
            monitor="val_auc", mode="max", save_best_only=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(monitor="val_auc", mode="max", factor=0.5, patience=1, min_lr=1e-5),
    ]

    history = model.fit(
        ds_train,
        validation_data=ds_val,
        epochs=args.epochs,
        callbacks=callbacks,
        # class_weight=class_weight,
        verbose=1,
    )

    # Évaluation test
    test_metrics = model.evaluate(ds_test, verbose=1)
    print("Test metrics:", dict(zip(model.metrics_names, test_metrics)))

    # --- Prédictions sur test pour matrice de confusion ---
    y_true = df_test["reverted"].values.astype(np.int32)

    # Probabilités
    y_prob = model.predict(ds_test, verbose=0).reshape(-1)

    # Seuil
    threshold = 0.5
    y_pred = (y_prob >= threshold).astype(np.int32)

    # Confusion matrix: [[TN, FP], [FN, TP]]
    cm = tf.math.confusion_matrix(y_true, y_pred, num_classes=2).numpy()
    tn, fp, fn, tp = cm.ravel()

    print("\n--- Confusion matrix (test) ---")
    print(cm)
    print(f"TN={tn}  FP={fp}  FN={fn}  TP={tp}")

    # Faux-positifs = modifications constructives détectées comme vandalismes
    print(f"\nFaux-positifs (constructif->vandalisme) : {fp}")

    # Optionnel: taux de faux positifs (FPR) et précision sur la classe 'vandalisme'
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    precision_pos = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    print(f"Taux de faux-positifs (FPR) : {fpr:.3f}")
    print(f"Precision (vandalisme) : {precision_pos:.3f}")

    # Sauvegarde modèle + normalisation features
    model.save(os.path.join(args.outdir, "model.keras"))
    with open(os.path.join(args.outdir, "num_feat_norm.json"), "w", encoding="utf-8") as f:
        json.dump({"mean": mean.to_dict(), "std": std.to_dict()}, f, ensure_ascii=False, indent=2)

    # Sauvegarde vocabs
    def save_vocab(vec, name):
        vocab = vec.get_vocabulary()
        with open(os.path.join(args.outdir, f"vocab_{name}.txt"), "w", encoding="utf-8") as f:
            for tok in vocab:
                f.write(tok + "\n")

    save_vocab(vec_old, "old")
    save_vocab(vec_new, "new")
    save_vocab(vec_diff, "diff")

    print(f"Modèle exporté dans: {args.outdir}/saved_model")

if __name__ == "__main__":
    main()