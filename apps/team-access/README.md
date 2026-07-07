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
