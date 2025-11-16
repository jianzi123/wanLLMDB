"""
Example: Training MNIST with PyTorch and wanLLMDB tracking.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms

import wanllmdb as wandb


# Define a simple CNN
class Net(nn.Module):
    def __init__(self):
        super(Net, self).__init__()
        self.conv1 = nn.Conv2d(1, 32, 3, 1)
        self.conv2 = nn.Conv2d(32, 64, 3, 1)
        self.dropout1 = nn.Dropout(0.25)
        self.dropout2 = nn.Dropout(0.5)
        self.fc1 = nn.Linear(9216, 128)
        self.fc2 = nn.Linear(128, 10)

    def forward(self, x):
        x = self.conv1(x)
        x = F.relu(x)
        x = self.conv2(x)
        x = F.relu(x)
        x = F.max_pool2d(x, 2)
        x = self.dropout1(x)
        x = torch.flatten(x, 1)
        x = self.fc1(x)
        x = F.relu(x)
        x = self.dropout2(x)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)


def train(model, device, train_loader, optimizer, epoch):
    model.train()
    for batch_idx, (data, target) in enumerate(train_loader):
        data, target = data.to(device), target.to(device)
        optimizer.zero_grad()
        output = model(data)
        loss = F.nll_loss(output, target)
        loss.backward()
        optimizer.step()

        # Log metrics
        if batch_idx % 10 == 0:
            wandb.log({
                "train/loss": loss.item(),
                "train/epoch": epoch,
            })

            print(f"Train Epoch: {epoch} [{batch_idx * len(data)}/{len(train_loader.dataset)} "
                  f"({100. * batch_idx / len(train_loader):.0f}%)]\tLoss: {loss.item():.6f}")


def test(model, device, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    with torch.no_grad():
        for data, target in test_loader:
            data, target = data.to(device), target.to(device)
            output = model(data)
            test_loss += F.nll_loss(output, target, reduction="sum").item()
            pred = output.argmax(dim=1, keepdim=True)
            correct += pred.eq(target.view_as(pred)).sum().item()

    test_loss /= len(test_loader.dataset)
    accuracy = 100. * correct / len(test_loader.dataset)

    # Log test metrics
    wandb.log({
        "test/loss": test_loss,
        "test/accuracy": accuracy,
    })

    print(f"\nTest set: Average loss: {test_loss:.4f}, "
          f"Accuracy: {correct}/{len(test_loader.dataset)} ({accuracy:.2f}%)\n")

    return test_loss, accuracy


def main():
    # Hyperparameters
    config = {
        "batch_size": 64,
        "test_batch_size": 1000,
        "epochs": 5,
        "learning_rate": 0.01,
        "momentum": 0.5,
        "seed": 42,
    }

    # Initialize wanLLMDB
    run = wandb.init(
        project="pytorch-mnist",
        name="cnn-baseline",
        config=config,
        tags=["pytorch", "cnn", "mnist"],
        notes="Baseline CNN model for MNIST classification",
    )

    # Set random seed
    torch.manual_seed(config["seed"])

    # Device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    # Data loaders
    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize((0.1307,), (0.3081,))
    ])

    train_dataset = datasets.MNIST("./data", train=True, download=True, transform=transform)
    test_dataset = datasets.MNIST("./data", train=False, transform=transform)

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=config["batch_size"],
        shuffle=True,
    )
    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=config["test_batch_size"],
        shuffle=False,
    )

    # Model, optimizer
    model = Net().to(device)
    optimizer = optim.SGD(
        model.parameters(),
        lr=config["learning_rate"],
        momentum=config["momentum"],
    )

    # Training loop
    best_accuracy = 0.0
    for epoch in range(1, config["epochs"] + 1):
        train(model, device, train_loader, optimizer, epoch)
        test_loss, accuracy = test(model, device, test_loader)

        # Update best accuracy
        if accuracy > best_accuracy:
            best_accuracy = accuracy
            wandb.summary["best_accuracy"] = best_accuracy
            # Save model
            torch.save(model.state_dict(), "mnist_cnn.pt")

    # Final summary
    wandb.summary["final_test_loss"] = test_loss
    wandb.summary["final_accuracy"] = accuracy

    # Finish run
    wandb.finish()
    print("Training complete!")


if __name__ == "__main__":
    main()
