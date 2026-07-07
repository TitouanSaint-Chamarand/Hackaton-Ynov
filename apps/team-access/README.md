# Team access (Phase B2)

Ce dossier versionne des comptes Kubernetes par membre via ServiceAccount.

## Ressources

- `apps/team-access/k8s/rbac-users.yaml`
  - 4 ServiceAccounts dans `demo` : `user-dev1` a `user-dev4`
  - 4 RoleBindings associes
  - droits `edit` pour `user-dev1` et `user-dev2`
  - droits `view` pour `user-dev3` et `user-dev4`

## Personnalisation

Avant demo finale, remplace les noms `user-dev*` par vos prenoms:

- `user-<prenom>`
- `user-<prenom>-binding`

Adapte aussi `roleRef.name` (`view` ou `edit`) selon le role de chaque membre.

## Verification des droits

Exemple de controle:

```bash
kubectl auth can-i get pods \
  --as=system:serviceaccount:demo:user-dev3 \
  -n demo

kubectl auth can-i create deployments \
  --as=system:serviceaccount:demo:user-dev3 \
  -n demo
```

## Generation des kubeconfigs individuels (Phase B2)

Un script est fourni pour generer un token temporaire et un kubeconfig par membre:

```bash
chmod +x scripts/team-access/generate-kubeconfigs.sh
./scripts/team-access/generate-kubeconfigs.sh demo user-dev1 user-dev2 user-dev3 user-dev4 --duration=48h
```

Les fichiers sont ecrits dans `generated-kubeconfigs/`:

- `generated-kubeconfigs/kubeconfig-user-dev1.yaml`
- `generated-kubeconfigs/kubeconfig-user-dev2.yaml`
- `generated-kubeconfigs/kubeconfig-user-dev3.yaml`
- `generated-kubeconfigs/kubeconfig-user-dev4.yaml`

Test rapide avec un kubeconfig individuel:

```bash
KUBECONFIG=generated-kubeconfigs/kubeconfig-user-dev3.yaml kubectl get pods -n demo
KUBECONFIG=generated-kubeconfigs/kubeconfig-user-dev3.yaml kubectl auth can-i create deployments -n demo
```
